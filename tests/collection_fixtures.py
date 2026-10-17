"""Synthetic classifiers, adapters, external payloads and provenance fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json

import pytest

from safira.adapters.base import ModelAdapter
from safira.adapters.capabilities import AdapterCapabilities


class SyntheticSourceContract:
    """One of two unrelated layouts, used only for generic ingestion tests."""

    def __init__(self, contract_id: str, version: str, layout: str) -> None:
        self.contract_id = contract_id
        self.version = version
        self.layout = layout

    def parse(self, raw_json):
        from safira.collection.precomputed import NormalizedEnvelope, OutputCandidate
        document = json.loads(raw_json)
        if self.layout == "flat":
            if set(document) - {"schema", "selector", "value", "class", "event", "association", "extension"}:
                raise ValueError("unknown field")
            if not {"schema", "selector", "value"} <= set(document):
                raise ValueError("required field missing")
            if document["schema"] != self.version:
                raise ValueError("version mismatch")
            outputs = (OutputCandidate(document["selector"], document["value"], "probability",
                                       "synthetic probability", "increasing", supplied_class=document.get("class"),
                                       event_id=document.get("event")),)
        else:
            if set(document) - {"release", "items", "association", "extension"}:
                raise ValueError("unknown field")
            if not {"release", "items"} <= set(document):
                raise ValueError("required field missing")
            if document["release"] != self.version or not isinstance(document["items"], list):
                raise ValueError("version mismatch")
            outputs = tuple(
                OutputCandidate(item["path"], item["reading"], "probability", "synthetic probability",
                                "increasing", supplied_class=item.get("class"), event_id=item.get("event"))
                for item in document["items"]
                if set(item) in ({"path", "reading"}, {"path", "reading", "event"},
                                 {"path", "reading", "class", "event"})
            )
            if len(outputs) != len(document["items"]):
                raise ValueError("invalid item")
        source_association = document.get("association")
        if source_association is not None:
            source_association = tuple(source_association)
        return NormalizedEnvelope(outputs, source_association)

    def validate_declarations(self, envelope, declarations):
        return envelope


from safira.collection.precomputed import ProvenanceCheck as SyntheticProvenanceCheck


class SyntheticTrustedVerifier:
    """Independent fixture ledger; entries are registered outside payloads."""

    integration_id = "synthetic-trusted-export-ledger"

    def __init__(self):
        self.entries = {}
        self.calls = []

    def add(self, event_id, raw_json, candidate, contribution, association):
        self.entries[event_id] = (
            sha256(raw_json.encode("utf-8") if isinstance(raw_json, str) else raw_json).hexdigest(),
            candidate.external_selector, contribution.source_key,
            (association.patient_ref, association.assessment_ref, association.occurrence_ref),
        )

    def check_output_link(self, raw_json, candidate, contributor, label, association):
        self.calls.append((raw_json, candidate, contributor.model_id, label.label_id, association))
        raw = raw_json.encode("utf-8") if isinstance(raw_json, str) else raw_json
        event_id = candidate.event_id
        expected = (
            sha256(raw).hexdigest(), candidate.external_selector,
            (contributor.model_id, contributor.model_version, label.label_id),
            (association.patient_ref, association.assessment_ref, association.occurrence_ref),
        )
        matched = self.entries.get(event_id) == expected
        return SyntheticProvenanceCheck(
            self.integration_id, "independent synthetic ledger comparison", "ledger-row-" + str(event_id),
            str(event_id), "sha256 of exact submitted bytes compared with independent ledger entry",
            matched, candidate.external_selector,
            (contributor.model_id, contributor.model_version, label.label_id),
            expected[3], matched, True, True, matched,
        )


@dataclass(frozen=True)
class CollectionClassifier:
    """An opaque synthetic classifier artifact with no clinical behavior."""

    artifact: bytes
    scores: dict[str, float]


class CollectionAdapter(ModelAdapter):
    """Deterministic test double that records primary and optional calls."""

    implementation_artifact = b"collection adapter synthetic v1"

    def __init__(
        self,
        classifier: CollectionClassifier,
        capabilities: AdapterCapabilities | None = None,
        evidence: dict[str, object] | None = None,
    ) -> None:
        super().__init__(capabilities or AdapterCapabilities(prediction_probability=True))
        self.classifier = classifier
        self.evidence = evidence or {}
        self.calls: list[tuple[str, str | None]] = []

    def predict(self, patient_data: object, label: str) -> float:
        self.calls.append(("predict", label))
        return self.classifier.scores[label]

    def predict_probability(self, patient_data: object, label: str) -> float:
        self.calls.append(("predict_probability", label))
        return self.classifier.scores[label]

    def extract_features(self, patient_data: object, label: str) -> object:
        self.calls.append(("extract_features", label))
        return self._item("feature_representation")

    def get_input_metadata(self, patient_data: object) -> dict[str, object]:
        self.calls.append(("get_input_metadata", None))
        return self._item("input_metadata")

    def _item(self, category):
        value = self.evidence.get(category)
        if isinstance(value, Exception):
            raise value
        return value

    def get_repeated_outputs(self, patient_data, label):
        self.calls.append(("get_repeated_outputs", label))
        return self._item("repeated_outputs")

    def get_modality_outputs(self, patient_data, label):
        self.calls.append(("get_modality_outputs", label))
        return self._item("modality_outputs")

    def get_domain_metadata(self, patient_data):
        self.calls.append(("get_domain_metadata", None))
        return self._item("domain_metadata")

    def explain(self, patient_data, label):
        self.calls.append(("explain", label))
        return self._item("explanation")

    def get_available_modalities(self, patient_data):
        self.calls.append(("get_available_modalities", None))
        return self._item("available_modalities")


@pytest.fixture
def registered_collection(tmp_path):
    """Register real Feature 001 bindings using a loader-owned synthetic pair."""
    from safira.registry import ModelRegistry, RegisteredModelVersion
    from safira.registry.identity import IdentityEvidence

    registry = ModelRegistry(tmp_path / "collection.sqlite3")

    def register(*, labels=("label-a",), kinds=None, scores=None,
                 model_id="synthetic-live", version="v1", capabilities=None,
                 evidence=None, modalities=()):
        classifier, _ = synthetic_pair(labels, scores)
        adapter = CollectionAdapter(classifier, capabilities, evidence)
        kinds = kinds or ("probability",) * len(labels)
        definition = RegisteredModelVersion.from_dict({
            "model_id": model_id, "model_version": version,
            "task_type": "supervised_single_label_binary_classification" if len(labels) == 1 else "supervised_multi_label_classification",
            "classifier_artifact": {"sha256": sha256(classifier.artifact).hexdigest()},
            "labels": [{
                "label_id": label, "negative_outcome": "negative", "positive_outcome": "positive",
                "output_selector": index, "value_kind": kind,
                "value_source": "predict_probability" if kind == "probability" else "predict",
                "value_scale": {"minimum": 0 if kind == "probability" else -2,
                                "maximum": 1 if kind == "probability" else 2,
                                "meaning": "synthetic probability" if kind == "probability" else "synthetic margin",
                                "positive_direction": "increasing"},
                "class_mapping": {"positive_when": ">=", "boundary": 0.6 if kind == "probability" else 0},
            } for index, (label, kind) in enumerate(zip(labels, kinds))],
            "adapter": {"adapter_id": "synthetic-live-adapter", "adapter_version": "v1",
                        "implementation_fingerprint": sha256(adapter.implementation_artifact).hexdigest(),
                        "associated_model_id": model_id, "associated_model_version": version,
                        "capabilities": adapter.capabilities.to_dict()},
            "input": {"schema": {"synthetic-feature": {"type": "float", "shape": [1]}},
                      "modalities": list(modalities)},
            "preprocessing_identity": "none",
        })

        class Loader:
            def identify_loaded_pair(self, actual_classifier, actual_adapter):
                return IdentityEvidence(
                    sha256(classifier.artifact).hexdigest(),
                    sha256(adapter.implementation_artifact).hexdigest(),
                    actual_classifier is classifier and actual_adapter is adapter
                    and adapter.classifier is classifier,
                )

        registry.register(definition, classifier, adapter, Loader())
        return definition, adapter

    yield registry, register
    registry.close()


def synthetic_pair(
    labels: tuple[str, ...] = ("label-a",),
    scores: tuple[float, ...] | None = None,
) -> tuple[CollectionClassifier, CollectionAdapter]:
    """Build either a one-label or a multi-label synthetic pair."""

    if scores is None:
        scores = tuple(0.2 + index * 0.2 for index in range(len(labels)))
    if not labels or len(labels) != len(scores):
        raise ValueError("Synthetic labels and scores must have equal nonzero length.")
    artifact = ("synthetic-collection:" + ",".join(labels)).encode("ascii")
    classifier = CollectionClassifier(artifact, dict(zip(labels, scores)))
    return classifier, CollectionAdapter(classifier)


def source_payload_a(selector: str, value: float, *, version: str = "v1") -> str:
    """Flat source contract shape, intentionally unlike source B."""

    return json.dumps({"schema_version": version, "selection": selector, "score": value})


def source_payload_b(selector: str, value: float, *, version: str = "2026-01") -> str:
    """Nested source contract shape, intentionally unlike source A."""

    return json.dumps({"release": version, "entries": [{"key": selector, "result": {"value": value}}]})


@dataclass
class SyntheticProvenanceManifest:
    """Independent fixture authority, never populated from submitted JSON."""

    entries: dict[str, tuple[str, tuple[str, str, str], tuple[str, str, str]]] = field(
        default_factory=dict
    )

    def add(
        self,
        event_id: str,
        covered_content: bytes,
        contributor: tuple[str, str, str],
        association: tuple[str, str, str],
    ) -> None:
        self.entries[event_id] = (
            sha256(covered_content).hexdigest(),
            contributor,
            association,
        )

    def matches(
        self,
        event_id: str,
        covered_content: bytes,
        contributor: tuple[str, str, str],
        association: tuple[str, str, str],
    ) -> bool:
        return self.entries.get(event_id) == (
            sha256(covered_content).hexdigest(),
            contributor,
            association,
        )


@pytest.fixture
def collection_single_pair() -> tuple[CollectionClassifier, CollectionAdapter]:
    return synthetic_pair()


@pytest.fixture
def collection_multi_pair() -> tuple[CollectionClassifier, CollectionAdapter]:
    return synthetic_pair(("label-a", "label-b"))


@pytest.fixture
def collection_manifest() -> SyntheticProvenanceManifest:
    return SyntheticProvenanceManifest()
