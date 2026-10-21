"""Private one-prediction Feature 004 application bridge."""

from hashlib import sha256
from types import SimpleNamespace

from safira.runtime._exceptions import RuntimeAdmissionRejected, RuntimeReadinessFailure


def _row_key(reference, prediction):
    from safira.signals.records import SignalRowKey
    from safira.signals.validation import prediction_fingerprint
    material = (f"{reference.dataset_id}\0{reference.manifest_reference}\0"
                f"{prediction_fingerprint(prediction)}").encode("utf-8")
    return SignalRowKey(sha256(material).hexdigest())


def reconstruct_runtime_references(admitted):
    """Reproduce exact frozen reference states using training predictors only.

    The routine reads each training row's prediction and patient-group key for
    Feature 004's frozen fold semantics. It never reads correctness labels,
    outcomes, validation/calibration rows, or protected-test content.
    """
    from safira.signals.reference import (ReferenceCompatibilityKey, ReferenceFitConfig,
        ReferenceObservation, fit_domain_reference, fit_knn_reference)
    from safira.signals.records import SignalSourceKey

    request = admitted.request
    protocol = request.original_signal_protocol
    reference = request.original_reference
    feature_set = request.original_signal_set
    expected = {(state.source_key.to_tuple(), state.method_id): state
                for state in feature_set.manifest.fitted_state_references
                if state.source_key.to_tuple() == admitted.scope_key}
    reconstructed = {}
    for method_id in sorted({"knn_distance", "domain_familiarity"}
                            & set(protocol.method_configs)):
        config = protocol.method_configs[method_id]
        params = config.parameters
        records = []
        fingerprints = set()
        for example in request.original_dataset.development.train:
            prediction = example.prediction
            if tuple(prediction.source_key) != admitted.scope_key:
                continue
            if example.partition_role != "train":
                raise RuntimeAdmissionRejected("original_inventory_incomplete")
            fingerprint = __import__("safira.signals.validation", fromlist=["prediction_fingerprint"]).prediction_fingerprint(prediction)
            if fingerprint in fingerprints:
                raise RuntimeAdmissionRejected("original_inventory_incomplete")
            fingerprints.add(fingerprint)
            row_key = _row_key(reference, prediction)
            evidence_category = ("feature_representation" if method_id == "knn_distance"
                                 else "domain_metadata")
            item = next((entry for entry in prediction.evidence
                         if entry.category == evidence_category), None)
            vector = category = None
            if item is not None and item.state == "available":
                if (item.interpretation.get("evidence_schema") == params["evidence_schema"]
                        and item.interpretation.get("preprocessing_identity")
                        == params["preprocessing_identity"]):
                    if method_id == "knn_distance":
                        vector = item.value
                    else:
                        category = item.value.get(params["category_field"])
            evidence_ref = sha256(f"{fingerprint}\0{evidence_category}".encode()).hexdigest()
            records.append(ReferenceObservation(
                row_key.value, SignalSourceKey(*admitted.scope_key), example.patient_group_ref,
                params["evidence_schema"], params["preprocessing_identity"],
                vector=vector, domain_category=category, evidence_ref=evidence_ref,
                partition_role="train",
            ))
        if not records:
            raise RuntimeAdmissionRejected("original_inventory_incomplete")
        source_key = SignalSourceKey(*admitted.scope_key)
        key = ReferenceCompatibilityKey(
            source_key, method_id, config.method_version, params, params["evidence_schema"],
            params["preprocessing_identity"], reference.dataset_id, reference.protocol_id,
            reference.protocol_version, reference.manifest_reference,
        )
        fit_config = ReferenceFitConfig(key, config, params["fold_count"], params["seed"])
        fit = fit_knn_reference if method_id == "knn_distance" else fit_domain_reference
        state = fit(tuple(records), fit_config)
        frozen = expected.get((admitted.scope_key, method_id))
        if (frozen is None or frozen.state_id != state.digest
                or frozen.dataset_id != reference.dataset_id
                or frozen.protocol_id != reference.protocol_id
                or frozen.protocol_version != reference.protocol_version
                or frozen.manifest_reference != reference.manifest_reference
                or frozen.method_version != config.method_version
                or frozen.preprocessing_identity != params["preprocessing_identity"]):
            raise RuntimeAdmissionRejected("signal_reference_incompatible")
        reconstructed[(admitted.scope_key, method_id)] = state
    if set(reconstructed) != set(expected):
        raise RuntimeAdmissionRejected("signal_reference_incompatible")
    return reconstructed


def derive_runtime_signal_record(admitted):
    """Build one private SignalFeatureRecord from the admitted prediction."""
    from safira.signals.base import SignalDimension, SignalState
    from safira.signals.records import SignalFeatureRecord, SignalResult, SignalSourceKey
    from safira.signals.reference import apply_domain_reference, apply_knn_reference
    from safira.signals.service import SignalExtractor

    from safira.runtime._verification import VerifiedRuntimeBundle
    if type(admitted) is not VerifiedRuntimeBundle:
        raise TypeError("runtime_bundle_invalid")
    request = admitted.request
    states = reconstruct_runtime_references(admitted)
    extractor = SignalExtractor(admitted.registry, request.original_signal_protocol,
                                admitted.verifier)
    raw = extractor.extract_record(request.prediction)
    by_method = {item.method_id: item for item in raw}
    configs = request.original_signal_protocol.method_configs
    specs = {item["method_id"]: item for item in request.estimator.feature_schema["feature_specs"]}
    output = []
    for method_id, config in configs.items():
        if method_id not in specs:
            raise RuntimeAdmissionRejected("signal_reference_incompatible")
        spec = specs[method_id]
        if method_id in ("knn_distance", "domain_familiarity"):
            state = states.get((admitted.scope_key, method_id))
            if state is None:
                raise RuntimeAdmissionRejected("signal_reference_incompatible")
            reference_method = ("feature_representation" if method_id == "knn_distance"
                                else "domain_metadata")
            query = SimpleNamespace(prediction=request.prediction)
            from safira.signals.service import SignalExtractor as _Extractor
            observation = _Extractor._reference_query(
                query, _row_key(request.original_reference, request.prediction),
                SignalSourceKey(*admitted.scope_key), method_id, config.parameters,
            )
            apply = apply_knn_reference if method_id == "knn_distance" else apply_domain_reference
            value = apply(state, observation.vector if method_id == "knn_distance"
                          else observation.domain_category, state.compatibility_key,
                          query_evidence_ref=observation.evidence_ref)
            state_value = SignalState(value.state)
            raw_result = SignalResult(
                SignalSourceKey(*admitted.scope_key), SignalDimension(spec["dimension"]),
                method_id, config.method_version, config.parameters, state_value, value.value,
                spec["meaning"], value.evidence_refs,
                {"reference_digest": state.digest}, value.reason_code,
                request.prediction.primary.to_dict(),
            )
        else:
            raw_result = by_method.get(method_id)
            if raw_result is None or (raw_result.method_version != config.method_version
                                      or dict(raw_result.method_parameters) != dict(config.parameters)):
                raise RuntimeAdmissionRejected("signal_reference_incompatible")
        output.append(raw_result)
    if set(by_method) != set(configs):
        raise RuntimeAdmissionRejected("signal_reference_incompatible")
    row_key = _row_key(request.original_reference, request.prediction)
    return SignalFeatureRecord(row_key, SignalSourceKey(*admitted.scope_key), tuple(output)), states


