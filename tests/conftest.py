"""Synthetic registry fixtures; no patient records or model dependencies."""

from dataclasses import dataclass
from hashlib import sha256

import pytest

from safira import AdapterCapabilities, ModelAdapter

from collection_fixtures import (
    collection_manifest, collection_multi_pair, collection_single_pair,
    registered_collection,
)


@dataclass(frozen=True)
class SyntheticClassifier:
    artifact: bytes


class SyntheticAdapter(ModelAdapter):
    implementation_artifact = b"synthetic adapter implementation v1"

    def __init__(self, classifier):
        super().__init__(AdapterCapabilities(prediction_probability=True))
        self.classifier = classifier

    def predict(self, patient_data, label):
        raise AssertionError("Registry foundations must not call prediction.")

    def predict_probability(self, patient_data, label):
        raise AssertionError("Registry foundations must not call probability.")


class SyntheticIdentityProvider:
    """Test loader that remembers the objects it created from known bytes."""

    def __init__(self, classifier_artifact):
        self.classifier_artifact = classifier_artifact
        self.classifier = SyntheticClassifier(classifier_artifact)
        self.adapter = SyntheticAdapter(self.classifier)
        self.adapter_artifact = self.adapter.implementation_artifact
        self.calls = []

    def identify_loaded_pair(self, classifier, adapter):
        from safira.registry.identity import IdentityEvidence

        self.calls.append((classifier, adapter))
        verified = (
            classifier is self.classifier
            and adapter is self.adapter
            and adapter.classifier is classifier
            and classifier.artifact == self.classifier_artifact
            and adapter.implementation_artifact == self.adapter_artifact
        )
        return IdentityEvidence(
            classifier_sha256=sha256(self.classifier_artifact).hexdigest(),
            adapter_sha256=sha256(self.adapter_artifact).hexdigest(),
            loaded_pair_verified=verified,
        )


@pytest.fixture
def catalog_path(tmp_path):
    return tmp_path / "registry.sqlite3"


@pytest.fixture
def synthetic_classifier_artifact():
    return b"synthetic multi-label classifier v1: label-a, label-b"


@pytest.fixture
def loaded_pair(synthetic_classifier_artifact):
    provider = SyntheticIdentityProvider(synthetic_classifier_artifact)
    return provider.classifier, provider.adapter, provider


@pytest.fixture
def synthetic_metadata(loaded_pair):
    classifier, adapter, _ = loaded_pair
    return {
        "model_id": "synthetic-model",
        "model_version": "v1",
        "metadata_schema_version": 1,
        "task_type": "supervised_multi_label_classification",
        "classifier_artifact": {"sha256": sha256(classifier.artifact).hexdigest()},
        "labels": [
            {
                "label_id": label,
                "negative_outcome": "negative",
                "positive_outcome": "positive",
                "output_selector": index,
                "value_kind": "probability",
                "value_source": "predict_probability",
                "value_scale": {
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "meaning": "synthetic positive-class probability",
                    "positive_direction": "increasing",
                },
                "class_mapping": {"positive_when": ">=", "boundary": 0.5},
            }
            for index, label in enumerate(("label-a", "label-b"))
        ],
        "adapter": {
            "adapter_id": "synthetic-adapter",
            "adapter_version": "v1",
            "implementation_fingerprint": sha256(
                adapter.implementation_artifact
            ).hexdigest(),
            "associated_model_id": "synthetic-model",
            "associated_model_version": "v1",
            "capabilities": adapter.capabilities.to_dict(),
        },
        "input": {
            "schema": {"synthetic-feature": {"type": "float", "shape": [1]}},
            "modalities": ["synthetic"],
        },
        "preprocessing_identity": "none",
    }
