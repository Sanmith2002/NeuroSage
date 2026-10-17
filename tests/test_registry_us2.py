"""T012/T014: exact-version persistence and reattachment with synthetic artifacts."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from conftest import SyntheticIdentityProvider
from safira.registry import (
    BindingMismatchError,
    DuplicateRegistrationError,
    ModelRegistry,
    IncompatibleAdapterError,
    RegisteredModelVersion,
    UnattachedModelError,
    UnknownModelError,
    UnknownVersionError,
)


def _review_catalog(template, mixed=False):
    records = []
    keys = (("model-a", "v1"), ("model-a", "v2"), ("model-a", "v3"),
            ("model-b", "v1"), ("model-c", "v1"))
    for index, (model_id, version) in enumerate(keys):
        artifact = f"synthetic classifier {model_id}/{version}"
        record = deepcopy(template)
        record.update(model_id=model_id, model_version=version)
        if mixed and index in (1, 3, 4):
            record["task_type"] = "supervised_single_label_binary_classification"
            record["labels"] = record["labels"][:1]
        record["classifier_artifact"]["sha256"] = sha256(artifact.encode()).hexdigest()
        record["adapter"].update(
            associated_model_id=model_id, associated_model_version=version,
            adapter_id=f"synthetic-adapter-{model_id}",
        )
        record["labels"][0]["positive_outcome"] = f"synthetic outcome {model_id}"
        record["input"]["schema"]["synthetic-feature"]["shape"] = [index + 1]
        record["preprocessing_identity"] = {"version": f"synthetic-transform-{version}"}
        records.append({"artifact": artifact, "metadata": record})
    return records


def _restart_worker(mode, catalog_path, manifest_path):
    """Executed as a standalone script in a fresh interpreter, never forked state."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    snapshots = []
    with ModelRegistry(catalog_path) as registry:
        for item in manifest:
            declared = RegisteredModelVersion.from_dict(item["metadata"])
            key = (declared.model_id, declared.model_version)
            if mode == "write":
                provider = SyntheticIdentityProvider(item["artifact"].encode())
                registry.register(declared, provider.classifier, provider.adapter, provider)
            else:
                assert registry.get_metadata(*key).to_dict() == item["metadata"]
                # Metadata survives; no executable association is inferred from it.
                with pytest.raises(UnattachedModelError):
                    registry.resolve_usable(*key)
                provider = SyntheticIdentityProvider(item["artifact"].encode())
                wrong = SyntheticIdentityProvider(b"different frozen synthetic classifier")
                with pytest.raises(BindingMismatchError):
                    registry.attach(*key, wrong.classifier, wrong.adapter, wrong,
                                    definition=declared)
                with pytest.raises(IncompatibleAdapterError):
                    registry.attach(*key, provider.classifier, wrong.adapter, provider,
                                    definition=declared)
                with pytest.raises(UnattachedModelError):
                    registry.resolve_usable(*key)
                # Discard the failed evidence call before checking successful attach.
                provider.calls.clear()
                registry.attach(
                    *key, provider.classifier, provider.adapter, provider,
                    definition=declared,
                )
            usable = registry.resolve_usable(*key)
            assert usable.classifier is provider.classifier
            assert usable.adapter is provider.adapter
            assert provider.calls == [(provider.classifier, provider.adapter)]
            snapshots.append(registry.get_metadata(*key).to_dict())
        with pytest.raises(UnknownVersionError):
            registry.get_metadata("model-a", "v4")
        with pytest.raises(UnknownVersionError):
            registry.resolve_usable("model-a", "latest")
        with pytest.raises(UnknownModelError):
            registry.get_metadata("absent-model", "v1")
    print(json.dumps({"pid": os.getpid(), "snapshots": snapshots}))


@pytest.mark.parametrize("mixed", [False, True])
def test_catalog_survives_writer_exit_and_exact_pairs_reattach_in_fresh_process(
    catalog_path, synthetic_metadata, tmp_path, mixed
):
    manifest = _review_catalog(synthetic_metadata, mixed=mixed)
    manifest_path = tmp_path / "synthetic-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    project_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    # Explicitly locate this checkout; no model objects or providers cross processes.
    environment["PYTHONPATH"] = str(project_root / "src")
    results = []
    for mode in ("write", "read"):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), mode,
             str(catalog_path), str(manifest_path)],
            cwd=tmp_path, env=environment, text=True, capture_output=True,
            timeout=30, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        results.append(json.loads(result.stdout))
    assert all(result["pid"] != os.getpid() for result in results)
    expected = [item["metadata"] for item in manifest]
    assert results[0]["snapshots"] == results[1]["snapshots"] == expected


@pytest.mark.parametrize("single_label", [False, True])
@pytest.mark.parametrize("change", [
    "classifier", "adapter_implementation", "adapter_id", "adapter_version",
    "capabilities", "label_scope", "output_mapping", "input_schema", "modalities",
    "preprocessing",
])
def test_changed_declarations_cannot_reattach_under_accepted_version(
    catalog_path, synthetic_metadata, loaded_pair, change, single_label
):
    if single_label:
        synthetic_metadata["task_type"] = "supervised_single_label_binary_classification"
        synthetic_metadata["labels"] = synthetic_metadata["labels"][:1]
    classifier, adapter, provider = loaded_pair
    declared = RegisteredModelVersion.from_dict(synthetic_metadata)
    changed = deepcopy(synthetic_metadata)
    if change == "classifier":
        changed["classifier_artifact"]["sha256"] = "0" * 64
    elif change == "adapter_implementation":
        changed["adapter"]["implementation_fingerprint"] = "0" * 64
    elif change in ("adapter_id", "adapter_version"):
        changed["adapter"][change] = "different"
    elif change == "capabilities":
        changed["adapter"]["capabilities"]["prediction_probability"] = False
    elif change == "label_scope":
        changed["labels"][0]["label_id"] = "different-label"
    elif change == "output_mapping":
        changed["labels"][0]["class_mapping"]["boundary"] = 0.75
    elif change == "input_schema":
        changed["input"]["schema"]["synthetic-feature"]["shape"] = [2]
    elif change == "modalities":
        changed["input"]["modalities"].append("different-modality")
    else:
        changed["preprocessing_identity"] = "different-transform"
    candidate = RegisteredModelVersion.from_dict(changed)
    with ModelRegistry(catalog_path) as registry:
        registry.register(declared, classifier, adapter, provider)
        prior = registry.resolve_usable(declared.model_id, declared.model_version)
        with pytest.raises(BindingMismatchError):
            registry.attach(
                declared.model_id, declared.model_version, classifier, adapter, provider,
                definition=candidate,
            )
        assert registry.resolve_usable(declared.model_id, declared.model_version) is prior
        assert registry.get_metadata(declared.model_id, declared.model_version) == declared


@pytest.mark.parametrize("single_label", [False, True])
@pytest.mark.parametrize("artifact_kind", ["classifier", "adapter"])
def test_fresh_provider_evidence_is_compared_with_stored_fingerprints(
    catalog_path, synthetic_metadata, loaded_pair, artifact_kind, single_label
):
    if single_label:
        synthetic_metadata["task_type"] = "supervised_single_label_binary_classification"
        synthetic_metadata["labels"] = synthetic_metadata["labels"][:1]
    classifier, adapter, provider = loaded_pair
    declared = RegisteredModelVersion.from_dict(synthetic_metadata)
    candidate = SyntheticIdentityProvider(provider.classifier_artifact)
    if artifact_kind == "classifier":
        candidate = SyntheticIdentityProvider(b"different synthetic classifier material")
    else:
        candidate.adapter_artifact = b"different synthetic adapter material"
        candidate.adapter.implementation_artifact = candidate.adapter_artifact
    # This loader truthfully attests the candidate pair, but its digest differs.
    evidence = candidate.identify_loaded_pair(candidate.classifier, candidate.adapter)
    assert evidence.loaded_pair_verified is True
    candidate.calls.clear()
    with ModelRegistry(catalog_path) as registry:
        registry.register(declared, classifier, adapter, provider)
        prior = registry.resolve_usable(declared.model_id, declared.model_version)
        with pytest.raises(BindingMismatchError):
            registry.attach(
                declared.model_id, declared.model_version,
                candidate.classifier, candidate.adapter, candidate, definition=declared,
            )
        assert candidate.calls == [(candidate.classifier, candidate.adapter)]
        assert registry.resolve_usable(declared.model_id, declared.model_version) is prior
        assert registry.get_metadata(declared.model_id, declared.model_version) == declared


def test_changed_material_is_accepted_only_under_new_version(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    original = RegisteredModelVersion.from_dict(synthetic_metadata)
    newer = SyntheticIdentityProvider(b"synthetic classifier material v2")
    changed = deepcopy(synthetic_metadata)
    changed["classifier_artifact"]["sha256"] = sha256(newer.classifier_artifact).hexdigest()
    changed["preprocessing_identity"] = "synthetic-transform-v2"
    with ModelRegistry(catalog_path) as registry:
        registry.register(original, classifier, adapter, provider)
        with pytest.raises(DuplicateRegistrationError):
            registry.register(
                RegisteredModelVersion.from_dict(changed),
                newer.classifier, newer.adapter, newer,
            )
        changed["model_version"] = "v2"
        changed["adapter"]["associated_model_version"] = "v2"
        version_two = RegisteredModelVersion.from_dict(changed)
        registry.register(version_two, newer.classifier, newer.adapter, newer)
        assert registry.get_metadata(original.model_id, "v1") == original
        assert registry.get_metadata(original.model_id, "v2") == version_two
        assert registry.resolve_usable(original.model_id, "v1").classifier is classifier
        assert registry.resolve_usable(original.model_id, "v2").classifier is newer.classifier


if __name__ == "__main__":
    _restart_worker(*sys.argv[1:])
