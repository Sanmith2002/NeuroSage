"""Synthetic classifiers, adapters, external payloads and provenance fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json

import pytest

from safira.adapters.base import ModelAdapter
from safira.adapters.capabilities import AdapterCapabilities


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
        return self.evidence["feature_representation"]

    def get_input_metadata(self, patient_data: object) -> dict[str, object]:
        self.calls.append(("get_input_metadata", None))
        return self.evidence["input_metadata"]  # type: ignore[return-value]


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
