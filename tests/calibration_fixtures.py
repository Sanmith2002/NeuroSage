"""Synthetic-only Feature 006 fixture helpers built on existing feature APIs."""

from __future__ import annotations

from training_fixtures import build_inputs, training_scope


def synthetic_development(registry, register, **kwargs):
    """Return independently scoped synthetic Feature 003/004 development inputs."""
    return build_inputs(registry, register, **kwargs)


def exact_scope(registry, model_id, model_version, label_id):
    return training_scope(registry, model_id, model_version, label_id)


def frozen_estimator_artifacts(service, dataset, signals):
    """Build selected Feature 005 artifacts through its existing synthetic service."""
    return tuple(outcome.artifact for outcome in service.train(dataset, signals)
                 if outcome.artifact is not None)


def supported_configurations():
    """Describe fixture shapes used by tests without disease-specific semantics."""
    return {
        "standalone_binary": (("model-a", "v1", "label-a"),),
        "multi_label": (("model-b", "v1", "label-a"), ("model-b", "v1", "label-b")),
        "independent_multi_model": (("model-c", "v1", "label-a"), ("model-d", "v2", "label-a")),
    }
