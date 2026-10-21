"""Private derivation of policy-cohort Feature 004 rows from admitted predictions."""

from __future__ import annotations

from hashlib import sha256

from safira.policy.exceptions import PolicyVerificationError
from safira.signals.base import SignalDimension, SignalState
from safira.signals.records import SignalFeatureRecord, SignalResult, SignalRowKey, SignalSourceKey
from safira.signals.service import SignalExtractor, _REFERENCE_METHODS
from safira.signals.validation import prediction_fingerprint, verify_and_validate_record


def _policy_row_key(reference, prediction):
    material = f"{reference.dataset_id}\0{reference.manifest_reference}\0{prediction_fingerprint(prediction)}".encode()
    return SignalRowKey(sha256(material).hexdigest())


def build_policy_signal_rows(dataset, reference, signal_protocol, extractor,
                             fitted_states, evidence_verifier, *, source_key=None):
    """Create validation rows only; no reference fitting uses this dataset."""
    from safira.signals.reference import apply_domain_reference, apply_knn_reference

    rows = []
    scope_filter = None if source_key is None else tuple(source_key)
    expected_sources = {item.to_tuple() for item in signal_protocol.source_keys}
    if scope_filter is not None and scope_filter not in expected_sources:
        raise PolicyVerificationError("scope_incompatible")
    examples = tuple(example for example in dataset.development.validation
                     if scope_filter is None or tuple(example.prediction.source_key) == scope_filter)
    seen = set()
    for example in examples:
        record = example.prediction
        source_tuple = tuple(record.source_key)
        if source_tuple not in {item.to_tuple() for item in signal_protocol.source_keys}:
            raise PolicyVerificationError("scope_incompatible")
        key = _policy_row_key(reference, record)
        if key.value in seen:
            raise PolicyVerificationError("inventory_mismatch")
        seen.add(key.value)
        checks = {item.method_id: item for item in extractor.extract_record(record)}
        verify_and_validate_record(extractor.registry, signal_protocol, evidence_verifier, record)
        source = SignalSourceKey(*source_tuple)
        for method_id in _REFERENCE_METHODS.intersection(signal_protocol.method_configs):
            config = signal_protocol.method_configs[method_id]
            state = fitted_states.get((source_tuple, method_id))
            if state is None:
                raise PolicyVerificationError("reference_reproduction_failed")
            evidence_category = ("feature_representation" if method_id == "knn_distance"
                                 else "domain_metadata")
            evidence_item = next((item for item in record.evidence
                                  if item.category == evidence_category), None)
            if (evidence_item is not None and evidence_item.state == "available"
                    and (evidence_item.interpretation.get("evidence_schema")
                         != config.parameters["evidence_schema"]
                         or evidence_item.interpretation.get("preprocessing_identity")
                         != config.parameters["preprocessing_identity"])):
                raise PolicyVerificationError("scope_incompatible")
            observation = SignalExtractor._reference_query(example, key, source, method_id, config.parameters)
            if method_id == "knn_distance":
                applied = apply_knn_reference(state, observation.vector, state.compatibility_key,
                                              query_evidence_ref=observation.evidence_ref)
                dimension = SignalDimension.DISTRIBUTION_CONFORMITY
                meaning = "Raw k-th-neighbour Euclidean distance; not a probability."
                category = "feature_representation"
            else:
                applied = apply_domain_reference(state, observation.domain_category, state.compatibility_key,
                                                 query_evidence_ref=observation.evidence_ref)
                dimension = SignalDimension.DOMAIN_FAMILIARITY
                meaning = "Seen/unseen membership in the compatible training-reference vocabulary."
                category = "domain_metadata"
            checks[method_id] = SignalResult(
                source, dimension, method_id, config.method_version, config.parameters,
                SignalState(applied.state), applied.value, meaning, (category,),
                {"reference_digest": state.digest, "reference_dataset_id": state.compatibility_key.dataset_id,
                 "reference_protocol_id": state.compatibility_key.protocol_id,
                 "reference_manifest": state.compatibility_key.manifest_reference,
                 "query_evidence_ref": observation.evidence_ref}, applied.reason_code,
                record.primary.to_dict(),
            )
        ordered = tuple(checks[item.method_id] for item in signal_protocol.method_configs.values()
                        if item.method_id in checks)
        rows.append(SignalFeatureRecord(key, source, ordered))
    if any(row.source_key.to_tuple() not in expected_sources for row in rows):
        raise PolicyVerificationError("scope_incompatible")
    return tuple(rows)

