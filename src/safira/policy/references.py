"""Private, training-only reconstruction of original Feature 004 reference states."""

from __future__ import annotations

from hashlib import sha256
from types import MappingProxyType

from safira.policy.exceptions import PolicyVerificationError
from safira.signals.records import SignalRowKey, SignalSourceKey
from safira.signals.validation import prediction_fingerprint


def _row_key(reference, prediction):
    material = f"{reference.dataset_id}\0{reference.manifest_reference}\0{prediction_fingerprint(prediction)}".encode()
    return SignalRowKey(sha256(material).hexdigest())


def reconstruct_original_references(dataset, reference, signal_protocol, feature_set):
    """Re-fit exactly the declared references from original training predictors only."""
    from safira.signals.reference import (ReferenceCompatibilityKey, ReferenceFitConfig,
        fit_domain_reference, fit_knn_reference)
    from safira.signals.service import SignalExtractor, _REFERENCE_METHODS

    if dataset.readiness.state != "ready" or dataset.manifest_reference != reference.manifest_reference:
        raise PolicyVerificationError("reference_reproduction_failed")
    expected_states = {(state.source_key.to_tuple(), state.method_id): state
                       for state in feature_set.manifest.fitted_state_references}
    reconstructed = {}
    for method_id in sorted(_REFERENCE_METHODS.intersection(signal_protocol.method_configs)):
        config = signal_protocol.method_configs[method_id]
        params = config.parameters
        for source in sorted({tuple(item.to_tuple()) for item in signal_protocol.source_keys}):
            training = tuple(example for example in dataset.development.train
                             if tuple(example.prediction.source_key) == source)
            if not training:
                continue
            source_key = SignalSourceKey(*source)
            key = ReferenceCompatibilityKey(
                source_key,
                method_id, config.method_version, params, params["evidence_schema"],
                params["preprocessing_identity"], reference.dataset_id, reference.protocol_id,
                reference.protocol_version, reference.manifest_reference,
            )
            fit_config = ReferenceFitConfig(key, config, params["fold_count"], params["seed"])
            observations = tuple(SignalExtractor._reference_observation(
                example, _row_key(reference, example.prediction), source_key,
                method_id, params) for example in training)
            fit = fit_knn_reference if method_id == "knn_distance" else fit_domain_reference
            state = fit(observations, fit_config)
            expected = expected_states.get((source, method_id))
            if (expected is None or expected.state_id != state.digest
                    or expected.dataset_id != reference.dataset_id
                    or expected.protocol_id != reference.protocol_id
                    or expected.protocol_version != reference.protocol_version
                    or expected.manifest_reference != reference.manifest_reference
                    or expected.method_version != config.method_version
                    or expected.preprocessing_identity != params["preprocessing_identity"]):
                raise PolicyVerificationError("reference_reproduction_failed")
            reconstructed[(source, method_id)] = state
    if set(reconstructed) != set(expected_states):
        raise PolicyVerificationError("reference_reproduction_failed")
    return MappingProxyType(reconstructed)

