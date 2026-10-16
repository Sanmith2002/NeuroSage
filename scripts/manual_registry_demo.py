r"""Beginner-friendly Safira Feature 001 demonstration using synthetic models only.

Run from the repository root in PowerShell:
    .\.venv\Scripts\python.exe .\scripts\manual_registry_demo.py

The coordinator owns temporary storage and launches a writer, waits for it to
exit, then launches a new reader. No existing registry or dataset is opened.
These are tiny test doubles, not fitted Random Forest or XGBoost estimators.
"""

from dataclasses import dataclass, field
from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


# Find this checkout even when launched from another working directory.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from safira import AdapterCapabilities, ModelAdapter
from safira.registry import (
    BindingMismatchError,
    DuplicateRegistrationError,
    IdentityEvidence,
    InvalidRegistrationError,
    ModelRegistry,
    RegisteredModelVersion,
    UnattachedModelError,
    UnknownVersionError,
    UnsupportedTaskError,
)


LABELS = ("AD", "PD")
CATALOG_NAME = "synthetic-registry.sqlite3"
MANIFEST_NAME = "synthetic-models.json"


class DemoFailure(RuntimeError):
    """A demonstrated behavior did not match the expected public contract."""


def require(condition, description):
    if not condition:
        raise DemoFailure(description)
    print(f"[PASS] {description}", flush=True)


def expect_rejection(description, error_type, operation):
    try:
        operation()
    except error_type as error:
        print(f"[PASS] {description}: {type(error).__name__}", flush=True)
        print(f"       Reason: {error}", flush=True)
    except Exception as error:
        raise DemoFailure(
            f"{description}: expected {error_type.__name__}, got {type(error).__name__}"
        ) from None
    else:
        raise DemoFailure(f"{description}: operation unexpectedly succeeded")


@dataclass
class Activity:
    counts: dict[str, int] = field(default_factory=lambda: {
        "prediction": 0,
        "primary model training": 0,
        "safety training": 0,
        "calibration": 0,
        "reliability assessment": 0,
    })

    def record(self, operation):
        self.counts[operation] += 1


class GuardedOperations:
    """Instrumentation only: any attempted training/assessment fails the demo."""

    def _unexpected(self, operation):
        self.activity.record(operation)
        raise DemoFailure(f"Registry unexpectedly requested {operation}")

    def fit(self, *args, **kwargs):
        self._unexpected("primary model training")

    def train_safety_package(self, *args, **kwargs):
        self._unexpected("safety training")

    def calibrate(self, *args, **kwargs):
        self._unexpected("calibration")

    def assess(self, *args, **kwargs):
        self._unexpected("reliability assessment")


@dataclass(frozen=True)
class RandomForestLike(GuardedOperations):
    """Pretend tree leaf probabilities; averaging would produce per-label scores."""

    leaves: tuple[tuple[float, ...], ...]
    activity: Activity

    def probability(self, synthetic_input, label):
        self.activity.record("prediction")
        probabilities = self.leaves[LABELS.index(label)]
        return sum(probabilities) / len(probabilities)


@dataclass(frozen=True)
class XGBoostLike(GuardedOperations):
    """Pretend tree contributions; summing would produce per-label raw margins."""

    base_margins: tuple[float, ...]
    contributions: tuple[tuple[float, ...], ...]
    activity: Activity

    def score(self, synthetic_input, label):
        self.activity.record("prediction")
        index = LABELS.index(label)
        return self.base_margins[index] + sum(self.contributions[index])


class ForestAdapter(GuardedOperations, ModelAdapter):
    def __init__(self, classifier, activity):
        super().__init__(AdapterCapabilities(prediction_probability=True))
        self.classifier = classifier
        self.activity = activity

    def predict(self, patient_data, label):
        return int(self.predict_probability(patient_data, label) >= 0.5)

    def predict_probability(self, patient_data, label):
        return self.classifier.probability(patient_data, label)


class BoostingAdapter(GuardedOperations, ModelAdapter):
    def __init__(self, classifier, activity):
        super().__init__(AdapterCapabilities())
        self.classifier = classifier
        self.activity = activity

    def predict(self, patient_data, label):
        # The approved contract uses predict() for declared non-probability scores.
        return self.classifier.score(patient_data, label)


class DemoLoader:
    """Trusted demo owner: load known JSON bytes and remember the actual live pair.

    This illustrates the existing IdentityProvider protocol. Artifact hashes alone
    do not prove the origin of arbitrary Python objects; the loader owns that link.
    """

    def __init__(self, artifact):
        self.artifact = artifact
        self.payload = json.loads(artifact)
        self.activity = Activity()
        if self.payload["family"] == "forest":
            self.classifier = RandomForestLike(
                tuple(tuple(row) for row in self.payload["leaves"]), self.activity
            )
            self.adapter = ForestAdapter(self.classifier, self.activity)
        else:
            self.classifier = XGBoostLike(
                tuple(self.payload["base_margins"]),
                tuple(tuple(row) for row in self.payload["contributions"]), self.activity,
            )
            self.adapter = BoostingAdapter(self.classifier, self.activity)
        self.definition = self._definition()

    def identify_loaded_pair(self, classifier, adapter):
        return IdentityEvidence(
            classifier_sha256=sha256(self.artifact).hexdigest(),
            adapter_sha256=sha256(inspect.getsource(type(self.adapter)).encode()).hexdigest(),
            loaded_pair_verified=(
                classifier is self.classifier and adapter is self.adapter
                and adapter.classifier is classifier
            ),
        )

    def _definition(self):
        probability = self.payload["family"] == "forest"
        model_id = "synthetic-rf" if probability else "synthetic-xgb"
        version = self.payload["version"]
        evidence = self.identify_loaded_pair(self.classifier, self.adapter)
        return RegisteredModelVersion.from_dict({
            "model_id": model_id, "model_version": version,
            "task_type": "supervised_multi_label_classification",
            "classifier_artifact": {"sha256": evidence.classifier_sha256},
            "labels": [
                {
                    "label_id": label, "negative_outcome": f"synthetic {label} negative",
                    "positive_outcome": f"synthetic {label} positive", "output_selector": label,
                    "value_kind": "probability" if probability else "continuous_score",
                    "value_source": "predict_probability" if probability else "predict",
                    "value_scale": {
                        "minimum": 0.0 if probability else None,
                        "maximum": 1.0 if probability else None,
                        "meaning": "primary positive-class probability estimate" if probability
                                   else "primary unbounded additive margin (not a probability)",
                        "positive_direction": "increasing",
                    },
                    # Illustrative PRIMARY classifier rules, not Safira safety cutoffs.
                    "class_mapping": {"positive_when": ">=", "boundary": 0.5 if probability else 0.0},
                }
                for label in LABELS
            ],
            "adapter": {
                "adapter_id": type(self.adapter).__name__, "adapter_version": "v1",
                "implementation_fingerprint": evidence.adapter_sha256,
                "associated_model_id": model_id, "associated_model_version": version,
                "capabilities": self.adapter.capabilities.to_dict(),
            },
            "input": {
                "schema": {"synthetic-vector": {"type": "float", "shape": [2]}},
                "modalities": ["synthetic"],
            },
            "preprocessing_identity": "none",
        })


def make_loader(family, version):
    payload = {"family": family, "version": version}
    if family == "forest":
        payload["leaves"] = (
            [[0.35, 0.65, 0.75], [0.25, 0.45, 0.55]] if version == "v1"
            else [[0.42, 0.64, 0.78], [0.20, 0.40, 0.60]]
        )
    else:
        payload.update(base_margins=[-0.2, 0.1], contributions=[[0.4, 0.3], [-0.1, 0.2]])
    return DemoLoader(json.dumps(payload, sort_keys=True).encode())


def show_metadata(definition):
    print(f"\n  Model: {definition.model_id} / {definition.model_version}")
    print(f"  Adapter: {definition.adapter.adapter_id} / {definition.adapter.adapter_version}")
    print(f"  Classifier SHA-256 prefix: {definition.classifier_artifact['sha256'][:16]}")
    for label in definition.labels:
        print(f"  {label.label_id}: {label.negative_outcome} | {label.positive_outcome}")
        print(f"      {label.value_kind} via {label.value_source}(); {label.value_scale['meaning']}")
        print(f"      Scale: {label.value_scale['minimum']} to {label.value_scale['maximum']}"
              f" (None means unbounded); primary positive rule: >= {label.class_mapping['boundary']}")
    print("  These are PRIMARY prediction declarations. No prediction or Safira reliability score is computed.")


def confirm_no_work(loaders):
    for operation in Activity().counts:
        total = sum(loader.activity.counts[operation] for loader in loaders)
        require(total == 0, f"{operation.capitalize()} calls = {total}")


def write_demo(workdir):
    print(f"\nSTEP 1: Register synthetic models (writer process {os.getpid()})", flush=True)
    forest = make_loader("forest", "v1")
    boosting = make_loader("boosting", "v1")
    newer = make_loader("forest", "v2")
    loaders = [forest, boosting, newer]
    catalog = workdir / CATALOG_NAME
    require(not catalog.exists(), "Using a fresh temporary catalog")
    with ModelRegistry(catalog) as registry:
        for loader in (forest, boosting):
            record = registry.register(loader.definition, loader.classifier, loader.adapter, loader)
            require(record == loader.definition, f"Registered {record.model_id}/{record.model_version}")
            show_metadata(record)
        print("\nSTEP 2: Retrieve both models independently", flush=True)
        for loader in (forest, boosting):
            record = registry.get_metadata(loader.definition.model_id, "v1")
            usable = registry.resolve_usable(record.model_id, "v1")
            require(record == loader.definition and usable.classifier is loader.classifier
                    and usable.adapter is loader.adapter,
                    f"Exact metadata and live pair retrieved for {record.model_id}/v1")
        print("\nSTEP 3: Add a new version without replacing the original", flush=True)
        original = registry.get_metadata("synthetic-rf", "v1").to_dict()
        registry.register(newer.definition, newer.classifier, newer.adapter, newer)
        require(registry.get_metadata("synthetic-rf", "v2") == newer.definition,
                "synthetic-rf/v2 is independently retrievable")
        require(registry.get_metadata("synthetic-rf", "v1").to_dict() == original,
                "synthetic-rf/v1 remains unchanged")
        print("\nSTEP 4: Expected rejections are successful safety checks", flush=True)
        expect_rejection("Duplicate registration rejected", DuplicateRegistrationError,
                         lambda: registry.register(forest.definition, forest.classifier, forest.adapter, forest))
        expect_rejection("Wrong adapter paired with the forest rejected", BindingMismatchError,
                         lambda: registry.attach("synthetic-rf", "v1", forest.classifier,
                                                 boosting.adapter, forest, definition=forest.definition))
        expect_rejection("v2 classifier cannot masquerade as v1", BindingMismatchError,
                         lambda: registry.attach("synthetic-rf", "v1", newer.classifier,
                                                 newer.adapter, newer, definition=forest.definition))
        expect_rejection("Unknown version is not replaced by another version", UnknownVersionError,
                         lambda: registry.get_metadata("synthetic-rf", "v99"))
        bad_schema = forest.definition.to_dict()
        bad_schema["labels"][1]["label_id"] = "AD"
        expect_rejection("Duplicate AD label schema rejected", InvalidRegistrationError,
                         lambda: registry.register(RegisteredModelVersion.from_dict(bad_schema),
                                                   forest.classifier, forest.adapter, forest))
        single_label = forest.definition.to_dict()
        single_label["labels"] = single_label["labels"][:1]
        expect_rejection("Standalone single-label classifier rejected", UnsupportedTaskError,
                         lambda: RegisteredModelVersion.from_dict(single_label))
        for loader in loaders:
            key = (loader.definition.model_id, loader.definition.model_version)
            require(registry.get_metadata(*key) == loader.definition
                    and registry.resolve_usable(*key).classifier is loader.classifier,
                    f"Accepted record and pair {key[0]}/{key[1]} survived all rejected attempts")
        manifest = [
            {"artifact": loader.artifact.decode(), "metadata": loader.definition.to_dict()}
            for loader in loaders
        ]
    (workdir / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    confirm_no_work(loaders)


def read_demo(workdir):
    print(f"\nSTEP 5: Verify persistence in a NEW reader process {os.getpid()}", flush=True)
    manifest = json.loads((workdir / MANIFEST_NAME).read_text(encoding="utf-8"))
    loaders = []
    with ModelRegistry(workdir / CATALOG_NAME) as registry:
        for item in manifest:
            metadata = item["metadata"]
            key = (metadata["model_id"], metadata["model_version"])
            require(registry.get_metadata(*key).to_dict() == metadata,
                    f"SQLite retained exact metadata for {key[0]}/{key[1]}")
            expect_rejection(f"{key[0]}/{key[1]} has no automatically restored live binding",
                             UnattachedModelError, lambda: registry.resolve_usable(*key))
            loader = DemoLoader(item["artifact"].encode())
            loaders.append(loader)
            usable = registry.attach(*key, loader.classifier, loader.adapter, loader,
                                     definition=loader.definition)
            require(registry.resolve_usable(*key) is usable
                    and usable.classifier is loader.classifier and usable.adapter is loader.adapter,
                    f"Fresh exact classifier-adapter pair validated and reattached for {key[0]}/{key[1]}")
    confirm_no_work(loaders)


def main():
    # Worker arguments are used only by this script's coordinator, not a registry CLI.
    if len(sys.argv) == 3 and sys.argv[1] in ("--writer", "--reader"):
        operation = write_demo if sys.argv[1] == "--writer" else read_demo
        operation(Path(sys.argv[2]))
        return 0
    if len(sys.argv) != 1:
        print("Run without arguments: python scripts/manual_registry_demo.py", flush=True)
        return 1
    print("Safira Feature 001: manual registry demonstration", flush=True)
    print("AD and PD are synthetic binary-outcome labels. No patient data is used.", flush=True)
    print("Forest/boosting models are lightweight illustrations, not fitted ML libraries.", flush=True)
    with TemporaryDirectory(prefix="safira-registry-demo-") as temporary:
        for worker in ("--writer", "--reader"):
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), worker, temporary],
                timeout=30, check=False,
            )
            require(result.returncode == 0, f"{worker[2:].capitalize()} process finished successfully")
            if worker == "--writer":
                print("\nWriter has EXITED. Launching a separate interpreter for restart verification.", flush=True)
    require(not Path(temporary).exists(), "Temporary catalog and synthetic artifacts removed")
    print("\nLIMITATIONS", flush=True)
    print("- Only supervised multi-label registration (two or more labels); standalone single-label classifiers are unsupported.")
    print("- Identity provenance depends on the trusted loader; a digest alone cannot prove an arbitrary live object's origin.")
    print("- Primary prediction scores/probabilities are distinct from future Safira reliability scores.")
    print("- Registration does not establish safety readiness, clinical validity, or a TRUST/CAUTION/DEFER status.")
    print("- Safira is a research prototype, not a clinically validated medical device.")
    print("\n[PASS] All manual registry demonstrations completed.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"[FAIL] {type(error).__name__}: {error}", flush=True)
        raise SystemExit(1)
