"""Batch A extraction orchestration; no primary inference or fitted references."""

from types import MappingProxyType

from safira.dataset.records import CorrectnessExample
from safira.registry import ModelRegistry
from safira.signals.exceptions import SignalInputError, SignalProtocolError
from safira.signals.records import SignalProtocol
from safira.signals.stateless import (
    _bernoulli_entropy,
    _evidence_coverage,
    _modality_jsd,
    _repeated_output_variance,
)
from safira.signals.validation import verify_and_validate_record


_BATCH_A_METHODS = {
    "evidence_coverage", "bernoulli_entropy", "modality_jsd", "repeated_output_variance",
}
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
    """Extract configured stateless signals from independently admitted records."""

    def __init__(self, registry: ModelRegistry, protocol: SignalProtocol, verifier):
        if not isinstance(registry, ModelRegistry) or type(protocol) is not SignalProtocol:
            raise SignalInputError("extractor_configuration_invalid")
        if verifier is None or not callable(getattr(verifier, "verify_prediction", None)):
            raise SignalProtocolError("trusted_verifier_required")
        if not protocol.method_configs:
            raise SignalProtocolError("method_configuration_required")
        for method_id, config in protocol.method_configs.items():
            if method_id not in _BATCH_A_METHODS:
                raise SignalProtocolError("method_not_available_in_batch_a")
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
                elif config.parameters:
                    raise ValueError
            except Exception:
                raise SignalProtocolError("method_parameters_invalid") from None
        self.registry = registry
        self.protocol = protocol
        self.verifier = verifier

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
            else:  # Constructor rejects this before any input is processed.
                raise SignalProtocolError("method_not_available_in_batch_a")
            # The exact protocol method version is part of every result lineage.
            if result.method_version != config.method_version:
                result = type(result)(
                    result.source_key, result.dimension, result.method_id, config.method_version,
                    result.method_parameters, result.state, result.value, result.meaning,
                    result.evidence_sources, result.provenance, result.reason_code,
                )
            results.append(result)
        return tuple(results)
