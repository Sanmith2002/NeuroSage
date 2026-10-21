"""Batch A verification and exact-scope eligibility; no candidate fitting."""

from __future__ import annotations

from hashlib import sha256

from safira.registry import ModelRegistry
from safira.signals.records import SignalFeatureSet
from safira.signals.validation import prediction_fingerprint

from safira.training.exceptions import TrainingInputError, TrainingVerificationError
from safira.training.records import (
    TrainingOutcome, TrainingProtocol, TrainingScope, TrainingStatus,
)
from safira.training.verification import _verify_training_inputs


class SafetyTrainingService:
    """Admit complete development inputs and report per-scope preparation status.

    Batch A intentionally has no fit, selection, estimator inference, or artifact
    publication path. ``prepare`` is the only public operation at this stage.
    """

    def __init__(self, registry: ModelRegistry, protocol: TrainingProtocol, input_verifier):
        if not isinstance(registry, ModelRegistry) or type(protocol) is not TrainingProtocol:
            raise TrainingInputError("training_configuration_invalid")
        self._registry = registry
        self._protocol = protocol
        self._verifier = input_verifier

    def prepare(self, dataset, signals: SignalFeatureSet) -> tuple[TrainingOutcome, ...]:
        if type(signals) is not SignalFeatureSet:
            raise TrainingInputError("signal_feature_set_invalid")
        # Shared admission failure prevents all per-scope eligibility claims.
        _verify_training_inputs(
            self._registry, dataset, signals, signals.dataset_reference, self._verifier,
            scopes=self._protocol.scopes,
        )
        examples_by_scope = {scope.source_key: [] for scope in self._protocol.scopes}
        signal_by_role = {"train": {}, "validation": {}}
        for role, feature_role in (("train", "training"), ("validation", "validation")):
            for row in getattr(signals, feature_role):
                signal_by_role[role][row.row_key.value] = row
        for example in dataset.development.train:
            examples_by_scope[tuple(example.prediction.source_key)].append(example)
        outcomes = []
        for scope in self._protocol.scopes:
            outcomes.append(self._scope_outcome(scope, examples_by_scope.get(scope.source_key, ()),
                                                dataset, signal_by_role, signals))
        return tuple(outcomes)

    def _scope_outcome(self, scope, examples, dataset, signal_by_role, signals):
        key = scope.source_key
        criteria = self._protocol.adequacy.get(key)
        required_present = key in self._protocol.required_signal_methods
        if criteria is None or not required_present:
            return TrainingOutcome(scope, TrainingStatus.NOT_READY, "scope_protocol_incomplete")

        group_targets = {}
        groups = set()
        for example in examples:
            group = example.patient_group_ref
            groups.add(group)
            group_targets.setdefault(group, set()).add(example.correctness_target)

        counts = {0: 0, 1: 0}
        for targets in group_targets.values():
            if len(targets) == 1:
                counts[next(iter(targets))] += 1
        if len(groups) < criteria.minimum_patient_groups:
            return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE,
                                   "patient_group_support_insufficient")
        if any(counts[target] < minimum
               for target, minimum in criteria.correctness_class_minimums.items()):
            return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE,
                                   "correctness_class_support_insufficient")

        methods_required = self._protocol.required_signal_methods[key]
        for role, feature_role in (("train", "training"), ("validation", "validation")):
            rows = tuple(getattr(dataset.development, role))
            if role == "validation" and not any(tuple(row.prediction.source_key) == key for row in rows):
                return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE,
                                       "validation_rows_unavailable")
            for example in rows:
                if tuple(example.prediction.source_key) != key:
                    continue
                prediction = example.prediction
                digest = sha256(
                    f"{signals.dataset_reference.dataset_id}\0{signals.dataset_reference.manifest_reference}\0"
                    f"{prediction_fingerprint(prediction)}".encode("utf-8")
                ).hexdigest()
                feature = signal_by_role[role].get(digest)
                if feature is None:
                    return TrainingOutcome(scope, TrainingStatus.UNAVAILABLE_REQUIRED_EVIDENCE,
                                           "aligned_training_features_unavailable")
                available = {}
                for result in feature.predictors:
                    if result.state.value == "invalid":
                        return TrainingOutcome(scope, TrainingStatus.INVALID_INPUT, "signal_input_invalid")
                    if result.state.value == "not_ready":
                        return TrainingOutcome(scope, TrainingStatus.NOT_READY, "signal_provenance_not_ready")
                    if result.method_id in available:
                        return TrainingOutcome(scope, TrainingStatus.INVALID_INPUT, "signal_method_duplicate")
                    available[result.method_id] = result
                for method_id in methods_required:
                    result = available.get(method_id)
                    if result is None or result.state.value != "available":
                        return TrainingOutcome(scope, TrainingStatus.UNAVAILABLE_REQUIRED_EVIDENCE,
                                               "required_signal_unavailable")

        if not examples:
            return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE,
                                   "training_rows_unavailable")
        return TrainingOutcome(scope, TrainingStatus.ELIGIBLE_FOR_CANDIDATE_FITTING,
                               limitations=("candidate_fitting_not_implemented_in_batch_a",))
