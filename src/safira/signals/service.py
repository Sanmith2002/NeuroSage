"""Signal extraction and verified Feature 003 development integration."""

import hashlib
import json
from types import MappingProxyType

from safira.dataset.records import CorrectnessExample
from safira.registry import ModelRegistry
from safira.signals.base import SignalDimension, SignalState
from safira.signals.exceptions import SignalInputError, SignalProtocolError, SignalVerificationError
from safira.signals.records import (Feature003DatasetReference, FittedStateReference,
    ProtectedApplyReceipt, ProtectedApplyRequest, SignalFeatureRecord, SignalFeatureSet,
    SignalMethodConfig, SignalProtocol, SignalResult, SignalRowKey, SignalRunManifest,
    SignalSourceKey)
from safira.signals.stateless import (
    _provenance,
    _bernoulli_entropy,
    _evidence_coverage,
    _modality_jsd,
    _repeated_output_variance,
    _explanation_applicability,
)
from safira.signals.validation import (prediction_fingerprint, validate_registered_record, verify_and_validate_record,
                                      verify_dataset_admission)


_BATCH_A_METHODS = {
    "evidence_coverage", "bernoulli_entropy", "modality_jsd", "repeated_output_variance",
    "explanation_applicability",
    "knn_distance", "domain_familiarity",
}
_REFERENCE_METHODS = {"knn_distance", "domain_familiarity"}
_EVIDENCE_CATEGORIES = frozenset({
    "feature_representation", "repeated_outputs", "modality_outputs", "domain_metadata",
    "explanation", "input_metadata", "available_modalities",
})


def _cohort_support_by_source(examples, *, required_correctness_classes=()):
    """Internal pure summary; not an admitted/public cohort-adequacy claim.

    Feature 003 inputs cannot be published through a public Feature 004 path before
    T028's trusted exact-dataset and embedded-prediction admission gate exists.
    """
    classes = tuple(required_correctness_classes)
    if any(type(value) is not int or value not in (0, 1) for value in classes):
        raise ValueError("correctness_classes")
    group_sets = {}
    class_sets = {}
    for example in examples:
        if type(example) is not CorrectnessExample:
            raise ValueError("cohort_example")
        prediction = example.prediction
        source = tuple(prediction.source_key)
        if len(source) != 3 or not all(type(value) is str and value for value in source):
            raise ValueError("cohort_source")
        if type(example.patient_group_ref) is not str or not example.patient_group_ref:
            raise ValueError("cohort_group")
        group_sets.setdefault(source, set()).add(example.patient_group_ref)
        if example.correctness_target in classes:
            class_sets.setdefault((source, example.correctness_target), set()).add(example.patient_group_ref)
    summary = {}
    for source, groups in group_sets.items():
        class_counts = {
            str(value): len(class_sets.get((source, value), set())) for value in classes
        }
        summary[source] = MappingProxyType({
            "unique_patient_groups": len(groups),
            "correctness_class_patient_groups": MappingProxyType(class_counts),
        })
    return MappingProxyType(summary)


class SignalExtractor:
    """Extract signals only after exact Feature 002/003 trusted admission."""

    def __init__(self, registry: ModelRegistry, protocol: SignalProtocol, verifier, *,
                 dataset_verifier=None, protected_apply=None):
        if not isinstance(registry, ModelRegistry) or type(protocol) is not SignalProtocol:
            raise SignalInputError("extractor_configuration_invalid")
        if verifier is None or not callable(getattr(verifier, "verify_prediction", None)):
            raise SignalProtocolError("trusted_verifier_required")
        if not protocol.method_configs:
            raise SignalProtocolError("method_configuration_required")
        for method_id, config in protocol.method_configs.items():
            if method_id not in _BATCH_A_METHODS:
                raise SignalProtocolError("method_not_available")
            if config.method_version != "v1":
                raise SignalProtocolError("method_version_unsupported")
            try:
                if method_id == "evidence_coverage":
                    required = config.parameters.get(
                        "required_evidence",
                        protocol.evidence_prerequisites.get("data_sufficiency", ()),
                    )
                    if not isinstance(required, (tuple, list)):
                        raise ValueError
                    if any(type(category) is not str or category not in _EVIDENCE_CATEGORIES
                           for category in required) or len(required) != len(set(required)):
                        raise ValueError
                elif method_id in ("bernoulli_entropy", "modality_jsd"):
                    if "log_base" not in config.parameters:
                        raise ValueError
                    base = config.parameters["log_base"]
                    if not (base == "e" and type(base) is str) and (
                        type(base) not in (int, float) or base <= 1
                    ):
                        raise ValueError
                elif method_id == "explanation_applicability":
                    if config.parameters:
                        raise ValueError
                elif method_id == "knn_distance":
                    required = ("k", "metric", "fold_count", "seed", "evidence_schema", "preprocessing_identity")
                    if any(name not in config.parameters for name in required):
                        raise ValueError
                    if (type(config.parameters["k"]) is not int or config.parameters["k"] < 1
                            or config.parameters["metric"] != "euclidean"
                            or type(config.parameters["fold_count"]) is not int
                            or config.parameters["fold_count"] < 2):
                        raise ValueError
                    if any(type(config.parameters[name]) is not str or not config.parameters[name].strip()
                           for name in ("seed", "evidence_schema", "preprocessing_identity")):
                        raise ValueError
                elif method_id == "domain_familiarity":
                    required = ("category_field", "category_mapping_version", "privacy_approval_ref",
                                "fold_count", "seed", "evidence_schema", "preprocessing_identity")
                    if any(name not in config.parameters for name in required):
                        raise ValueError
                    if (type(config.parameters["fold_count"]) is not int
                            or config.parameters["fold_count"] < 2):
                        raise ValueError
                    if any(type(config.parameters[name]) is not str or not config.parameters[name].strip()
                           for name in ("category_field", "category_mapping_version", "privacy_approval_ref",
                                        "seed", "evidence_schema", "preprocessing_identity")):
                        raise ValueError
                elif config.parameters:
                    raise ValueError
            except Exception:
                raise SignalProtocolError("method_parameters_invalid") from None
        fold_scopes = {(cfg.parameters["seed"], cfg.parameters["fold_count"])
                       for key, cfg in protocol.method_configs.items() if key in _REFERENCE_METHODS}
        if len(fold_scopes) > 1:
            raise SignalProtocolError("reference_fold_configuration_mismatch")
        self.registry = registry
        self.protocol = protocol
        self.verifier = verifier
        self.dataset_verifier = dataset_verifier
        self.protected_apply = protected_apply

    def extract_record(self, record):
        """Admit one exact record and calculate only explicitly configured methods."""
        check = verify_and_validate_record(self.registry, self.protocol, self.verifier, record)
        results = []
        for method_id, config in self.protocol.method_configs.items():
            if method_id == "evidence_coverage":
                required = config.parameters.get(
                    "required_evidence",
                    self.protocol.evidence_prerequisites.get("data_sufficiency", ()),
                )
                result = _evidence_coverage(record, required, admission_check=check)
            elif method_id == "bernoulli_entropy":
                result = _bernoulli_entropy(record, log_base=config.parameters["log_base"], admission_check=check)
            elif method_id == "modality_jsd":
                result = _modality_jsd(record, log_base=config.parameters["log_base"], admission_check=check)
            elif method_id == "repeated_output_variance":
                result = _repeated_output_variance(record, admission_check=check)
            elif method_id == "explanation_applicability":
                result = _explanation_applicability(record, admission_check=check)
            elif method_id in _REFERENCE_METHODS:
                dimension = (SignalDimension.DISTRIBUTION_CONFORMITY if method_id == "knn_distance"
                            else SignalDimension.DOMAIN_FAMILIARITY)
                result = SignalResult(SignalSourceKey(*record.source_key), dimension, method_id,
                    config.method_version, config.parameters, SignalState.NOT_READY, None,
                    "Reference-based signal requires a verified Feature 003 dataset.", (),
                    {"admission_evidence_ref": check.evidence_ref}, "reference_not_ready",
                    record.primary.to_dict())
            else:  # Constructor rejects this before any input is processed.
                raise SignalProtocolError("method_not_available_in_batch_a")
            # The exact protocol method version is part of every result lineage.
            if result.method_version != config.method_version:
                result = type(result)(
                    result.source_key, result.dimension, result.method_id, config.method_version,
                    result.method_parameters, result.state, result.value, result.meaning,
                    result.evidence_sources, result.provenance, result.reason_code, result.primary_output,
                )
            results.append(result)
        return tuple(results)

    def build_feature_set(self, dataset, reference: Feature003DatasetReference) -> SignalFeatureSet:
        """Build development-only predictor rows after full independent admission."""
        from safira.signals.reference import (
            ReferenceCompatibilityKey, ReferenceFitConfig, ReferenceObservation,
            apply_domain_reference, apply_knn_reference, crossfit_domain, crossfit_knn,
            fit_domain_reference, fit_knn_reference,
        )
        dataset_verifier = self.dataset_verifier
        if dataset_verifier is None and callable(getattr(self.verifier, "verify_dataset", None)):
            dataset_verifier = self.verifier
        admitted_dataset = verify_dataset_admission(dataset_verifier, self.verifier, dataset, reference)
        if not reference.manifest_digest and admitted_dataset.manifest_digest:
            reference = Feature003DatasetReference(
                reference.dataset_id, reference.protocol_id, reference.protocol_version,
                reference.manifest_reference, reference.builder_version,
                admitted_dataset.manifest_digest,
            )
        if (reference.protocol_id != self.protocol.protocol_id
                or reference.protocol_version != self.protocol.protocol_version):
            raise SignalVerificationError("dataset_protocol_mismatch")

        partitions = {role: tuple(getattr(dataset.development, role))
                      for role in ("train", "validation", "calibration")}
        examples = tuple(example for role in partitions for example in partitions[role])
        # Validate every exact registration/evidence association before fitting any
        # local reference state; no partial state is returned on a mismatch.
        for example in examples:
            metadata, _ = validate_registered_record(self.registry, self.protocol, example.prediction)
            expected_preprocessing = metadata.preprocessing_identity
            if not isinstance(expected_preprocessing, str):
                expected_preprocessing = json.dumps(dict(expected_preprocessing), sort_keys=True,
                                                    separators=(",", ":"))
            for method_id in _REFERENCE_METHODS.intersection(self.protocol.method_configs):
                if (tuple(example.prediction.source_key) in [key.to_tuple() for key in self.protocol.source_keys]
                        and self.protocol.method_configs[method_id].parameters["preprocessing_identity"]
                        != expected_preprocessing):
                    raise SignalInputError("reference_preprocessing_mismatch")
        sources = {SignalSourceKey(*example.prediction.source_key) for example in examples}
        if not sources.issubset(set(self.protocol.source_keys)):
            raise SignalVerificationError("dataset_source_outside_protocol")

        row_keys = {}
        for example in examples:
            digest = prediction_fingerprint(example.prediction)
            material = f"{reference.dataset_id}\0{reference.manifest_reference}\0{digest}".encode("utf-8")
            row_keys[id(example)] = SignalRowKey(hashlib.sha256(material).hexdigest())

        reference_values = {}
        reference_prerequisites = {}
        fitted_states = {}
        for method_id in _REFERENCE_METHODS.intersection(self.protocol.method_configs):
            method = self.protocol.method_configs[method_id]
            for source in sorted(sources):
                training = [example for example in partitions["train"]
                            if tuple(example.prediction.source_key) == source.to_tuple()]
                if not training:
                    continue
                params = method.parameters
                key = ReferenceCompatibilityKey(
                    source, method_id, method.method_version, params,
                    params["evidence_schema"], params["preprocessing_identity"],
                    reference.dataset_id, reference.protocol_id, reference.protocol_version,
                    reference.manifest_reference,
                )
                fit_config = ReferenceFitConfig(key, method, params["fold_count"], params["seed"])
                observations_list = []
                for example in training:
                    observation = self._reference_observation(
                        example, row_keys[id(example)], source, method_id, params
                    )
                    observations_list.append(observation)
                    state, reason = self._reference_evidence_state(example.prediction, method_id, params)
                    reference_prerequisites[(source, method_id, row_keys[id(example)].value)] = (state, reason)
                observations = tuple(observations_list)
                dimensions = {len(row.vector) for row in observations if row.vector is not None}
                if method_id == "knn_distance" and len(dimensions) > 1:
                    for example in examples:
                        if tuple(example.prediction.source_key) != source.to_tuple():
                            continue
                        reference_prerequisites[(source, method_id, row_keys[id(example)].value)] = (
                            SignalState.INVALID, "representation_invalid")
                    continue
                crossfit = crossfit_knn if method_id == "knn_distance" else crossfit_domain
                fit = fit_knn_reference if method_id == "knn_distance" else fit_domain_reference
                fitted = fit(observations, fit_config)
                fitted_states[(source, method_id)] = fitted
                for value in crossfit(observations, fit_config):
                    reference_values[(source, method_id, value.row_key)] = value
                for role in ("validation", "calibration"):
                    for example in partitions[role]:
                        if tuple(example.prediction.source_key) != source.to_tuple():
                            continue
                        prereq_state, prereq_reason = self._reference_evidence_state(
                            example.prediction, method_id, params
                        )
                        reference_prerequisites[(source, method_id, row_keys[id(example)].value)] = (
                            prereq_state, prereq_reason)
                        if prereq_state is not SignalState.AVAILABLE:
                            continue
                        observation = self._reference_query(
                            example, row_keys[id(example)], source, method_id, params
                        )
                        if method_id == "knn_distance":
                            value = apply_knn_reference(fitted, observation.vector, key,
                                                        query_evidence_ref=observation.evidence_ref)
                        else:
                            value = apply_domain_reference(fitted, observation.domain_category, key,
                                                           query_evidence_ref=observation.evidence_ref)
                        reference_values[(source, method_id, observation.row_key)] = value

        safe_states = tuple(FittedStateReference(
            state.digest, source, method_id, state.method_config.method_version,
            reference.dataset_id, reference.protocol_id, reference.protocol_version,
            reference.manifest_reference, state.compatibility_key.preprocessing_identity,
            {"digest": state.digest, "evidence_schema": state.compatibility_key.evidence_schema,
             "reference_cohort": "training"},
        ) for (source, method_id), state in sorted(
            fitted_states.items(), key=lambda item: (item[0][0], item[0][1])))

        def make_rows(role):
            result_rows = []
            for example in partitions[role]:
                record = example.prediction
                source = SignalSourceKey(*record.source_key)
                signals = list(self.extract_record(record))
                admission = verify_and_validate_record(self.registry, self.protocol, self.verifier, record)
                for method_id in _REFERENCE_METHODS.intersection(self.protocol.method_configs):
                    method = self.protocol.method_configs[method_id]
                    row_id = row_keys[id(example)].value
                    prereq_state, prereq_reason = reference_prerequisites.get(
                        (source, method_id, row_id), (SignalState.MISSING, "representation_missing"))
                    value = reference_values.get((source, method_id, row_id))
                    signals = [signal for signal in signals if signal.method_id != method_id]
                    dimension = (SignalDimension.DISTRIBUTION_CONFORMITY if method_id == "knn_distance"
                                 else SignalDimension.DOMAIN_FAMILIARITY)
                    if prereq_state is not SignalState.AVAILABLE:
                        signals.append(SignalResult(
                            source, dimension, method_id, method.method_version, method.parameters,
                            prereq_state, None,
                            ("Raw k-th-neighbour Euclidean distance; not a probability."
                             if method_id == "knn_distance" else
                             "Seen/unseen membership in the compatible training-reference vocabulary."),
                            ("feature_representation" if method_id == "knn_distance" else "domain_metadata",),
                            {"dataset_id": reference.dataset_id,
                             "manifest_reference": reference.manifest_reference}, prereq_reason,
                            record.primary.to_dict(),
                        ))
                        continue
                    if value is None:
                        value = None
                        value_state = SignalState.NOT_READY
                        value_reason = "reference_not_ready"
                    else:
                        value_state = SignalState(value.state)
                        value_reason = value.reason_code
                    signals.append(SignalResult(
                        source, dimension, method_id, method.method_version, method.parameters,
                        value_state, value.value,
                        ("Raw k-th-neighbour Euclidean distance; not a probability."
                         if method_id == "knn_distance" else
                         "Seen/unseen membership in the compatible training-reference vocabulary."),
                        ("feature_representation" if method_id == "knn_distance" else "domain_metadata",),
                        {"prediction_lineage": _provenance(record, admission,
                             ("feature_representation" if method_id == "knn_distance" else "domain_metadata",)),
                         "dataset_id": reference.dataset_id,
                         "manifest_reference": reference.manifest_reference,
                         "reference_digest": value.reference_digest,
                         "evidence_refs": value.evidence_refs, "fold_id": value.fold_id},
                        value_reason,
                        record.primary.to_dict(),
                    ))
                result_rows.append(SignalFeatureRecord(row_keys[id(example)], source, tuple(signals)))
            return tuple(result_rows)

        support = {}
        for source in sorted(sources):
            count = len({example.patient_group_ref for example in partitions["train"]
                         if tuple(example.prediction.source_key) == source.to_tuple()})
            support[json.dumps(source.to_tuple(), separators=(",", ":"))] = {
                "training_patient_groups": count}
        seeds = {cfg.parameters["seed"] for key, cfg in self.protocol.method_configs.items()
                 if key in _REFERENCE_METHODS}
        folds = {cfg.parameters["fold_count"] for key, cfg in self.protocol.method_configs.items()
                 if key in _REFERENCE_METHODS}
        manifest = SignalRunManifest(
            reference, tuple(sorted(sources)), tuple(self.protocol.method_configs.values()), safe_states,
            (), next(iter(seeds)) if len(seeds) == 1 else "",
            next(iter(folds)) if len(folds) == 1 else 0,
        )
        return SignalFeatureSet(reference, make_rows("train"), make_rows("validation"),
                                make_rows("calibration"), manifest, support)

    @staticmethod
    def _reference_observation(example, row_key, source, method_id, params):
        from safira.signals.reference import ReferenceObservation
        record = example.prediction
        categories = {item.category: item for item in record.evidence}
        evidence_category = "feature_representation" if method_id == "knn_distance" else "domain_metadata"
        item = categories.get(evidence_category)
        vector = category = None
        if item is not None and item.state == "available":
            if (item.interpretation.get("evidence_schema") == params["evidence_schema"]
                    and item.interpretation.get("preprocessing_identity") == params["preprocessing_identity"]):
                if method_id == "knn_distance":
                    vector = item.value
                else:
                    category = item.value.get(params["category_field"])
                    if type(category) is not str:
                        category = None
        evidence_ref = hashlib.sha256(
            f"{prediction_fingerprint(record)}\0{evidence_category}".encode("utf-8")
        ).hexdigest()
        # ReferenceObservation is an internal object; the group is used only for
        # fold assignment/exclusion and is absent from its repr and outputs.
        return ReferenceObservation(
            row_key.value, source, example.patient_group_ref, params["evidence_schema"],
            params["preprocessing_identity"], vector=vector, domain_category=category,
            evidence_ref=evidence_ref, partition_role="train",
        )

    @staticmethod
    def _reference_evidence_state(record, method_id, params):
        category = "feature_representation" if method_id == "knn_distance" else "domain_metadata"
        item = next((value for value in record.evidence if value.category == category), None)
        if item is None:
            return SignalState.MISSING, "representation_missing" if method_id == "knn_distance" else "domain_evidence_missing"
        if item.state != "available":
            return SignalState(item.state), "representation_missing" if method_id == "knn_distance" else "domain_evidence_missing"
        if item.interpretation.get("evidence_schema") != params["evidence_schema"]:
            return SignalState.INVALID, "reference_schema_mismatch"
        if item.interpretation.get("preprocessing_identity") != params["preprocessing_identity"]:
            return SignalState.INVALID, "reference_state_invalid"
        if method_id == "knn_distance":
            try:
                vector = tuple(float(value) for value in item.value)
                if not vector or any(not __import__("math").isfinite(value) for value in vector):
                    raise ValueError
            except Exception:
                return SignalState.INVALID, "representation_invalid"
        else:
            value = item.value.get(params["category_field"])
            if value is None:
                return SignalState.MISSING, "domain_evidence_missing"
            if (type(value) is not str or not value.strip() or value != value.strip()):
                return SignalState.INVALID, "domain_category_invalid"
        return SignalState.AVAILABLE, None

    @staticmethod
    def _reference_query(example, row_key, source, method_id, params):
        """Build a query-only value without representing it as a training row."""
        from types import SimpleNamespace
        record = example.prediction
        item = next((value for value in record.evidence if value.category ==
                     ("feature_representation" if method_id == "knn_distance" else "domain_metadata")), None)
        vector = item.value if method_id == "knn_distance" else None
        category = (item.value.get(params["category_field"]) if item is not None
                    and method_id == "domain_familiarity" else None)
        ref = hashlib.sha256(f"{prediction_fingerprint(record)}\0{item.category}".encode("utf-8")).hexdigest()
        return SimpleNamespace(row_key=row_key.value, vector=vector, domain_category=category, evidence_ref=ref)

    def apply_protected(self, request: ProtectedApplyRequest) -> ProtectedApplyReceipt:
        if type(request) is not ProtectedApplyRequest:
            raise SignalInputError("protected_request_invalid")
        if self.protected_apply is None or not callable(getattr(self.protected_apply, "apply_frozen_state", None)):
            raise SignalVerificationError("protected_custodian_not_ready")
        try:
            receipt = self.protected_apply.apply_frozen_state(request)
        except Exception:
            raise SignalVerificationError("protected_handoff_failed") from None
        if type(receipt) is not ProtectedApplyReceipt:
            raise SignalVerificationError("protected_receipt_invalid")
        expected = (request.fingerprint, request.dataset_reference,
                    tuple(ref.state_id for ref in request.fitted_state_references), request.method_scope)
        actual = (receipt.request_fingerprint, receipt.dataset_reference, receipt.state_ids, receipt.method_scope)
        if (receipt.status != "accepted" or actual != expected or not receipt.authority.strip()
                or not receipt.evidence_ref.strip()):
            raise SignalVerificationError("protected_receipt_mismatch")
        return receipt
