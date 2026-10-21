"""Trusted Feature 005 training orchestration for independent exact scopes."""

from __future__ import annotations

from hashlib import sha256
import json

from safira.registry import ModelRegistry
from safira.signals.records import SignalFeatureSet
from safira.signals.validation import prediction_fingerprint
from safira.training.candidates import (
    CandidateStatus, SelectionStatus, _candidate_probability, compare_candidates,
    fit_logistic_candidate, fit_prevalence_baseline, runtime_versions,
)
from safira.training.exceptions import TrainingInputError, TrainingVerificationError
from safira.training.features import (
    build_feature_schema, fit_preprocessing, transform_rows,
)
from safira.training.records import (
    CandidateFailurePolicy, FeaturePolicy, LogisticCandidateConfig, PreprocessingPolicy,
    SafetyEstimatorArtifact, TrainingOutcome, TrainingProtocol, TrainingScope, TrainingStatus,
    ValidationSupportCriteria,
)
from safira.training.verification import _verify_training_inputs


class SafetyTrainingService:
    """Admit complete sources, fit candidates on train and select once on validation."""

    def __init__(self, registry: ModelRegistry, protocol: TrainingProtocol, input_verifier):
        if not isinstance(registry, ModelRegistry) or type(protocol) is not TrainingProtocol:
            raise TrainingInputError("training_configuration_invalid")
        self._registry = registry
        self._protocol = protocol
        self._verifier = input_verifier

    def prepare(self, dataset, signals: SignalFeatureSet) -> tuple[TrainingOutcome, ...]:
        """Report eligibility only; this operation does not fit or publish an artifact."""
        verified = self._admit(dataset, signals)
        return self._prepare_admitted(dataset, signals)

    def train(self, dataset, signals: SignalFeatureSet) -> tuple[TrainingOutcome, ...]:
        """Train independently per exact scope after complete trusted input admission."""
        verified = self._admit(dataset, signals)
        eligible = self._prepare_admitted(dataset, signals)
        outcomes = []
        for prepared in eligible:
            if prepared.status is not TrainingStatus.ELIGIBLE_FOR_CANDIDATE_FITTING:
                outcomes.append(prepared)
                continue
            scope = prepared.scope
            if not self._training_configuration_ready(scope):
                outcomes.append(TrainingOutcome(scope, TrainingStatus.NOT_READY, "scope_protocol_incomplete"))
                continue
            try:
                outcome = self._train_scope(dataset, signals, scope, verified)
            except Exception:
                # Avoid raw identifiers, values and dependency exception details.
                outcome = TrainingOutcome(scope, TrainingStatus.INVALID_INPUT, "training_features_invalid")
            outcomes.append(outcome)
        return tuple(outcomes)

    def _admit(self, dataset, signals):
        if type(signals) is not SignalFeatureSet:
            raise TrainingInputError("signal_feature_set_invalid")
        # This independently executes the Feature 002/003/004 admission boundary.
        return _verify_training_inputs(self._registry, dataset, signals, signals.dataset_reference,
                                       self._verifier, scopes=self._protocol.scopes)

    def _training_configuration_ready(self, scope):
        key = scope.source_key
        return (
            type(self._protocol.feature_policies.get(key)) is FeaturePolicy
            and type(self._protocol.preprocessing_policies.get(key)) is PreprocessingPolicy
            and type(self._protocol.logistic_configs.get(key)) is LogisticCandidateConfig
            and self._protocol.logistic_configs[key].approved
            and type(self._protocol.validation_adequacy.get(key)) is ValidationSupportCriteria
            and type(self._protocol.candidate_failure_policies.get(key)) is CandidateFailurePolicy
        )

    def _prepare_admitted(self, dataset, signals):
        examples_by_scope = {scope.source_key: [] for scope in self._protocol.scopes}
        signal_by_role = {"train": {}, "validation": {}}
        for role, feature_role in (("train", "training"), ("validation", "validation")):
            for row in getattr(signals, feature_role):
                signal_by_role[role][row.row_key.value] = row
        for example in dataset.development.train:
            examples_by_scope[tuple(example.prediction.source_key)].append(example)
        return tuple(self._scope_outcome(scope, examples_by_scope.get(scope.source_key, ()), dataset,
                                         signal_by_role, signals) for scope in self._protocol.scopes)

    def _scope_outcome(self, scope, examples, dataset, signal_by_role, signals):
        key = scope.source_key
        criteria = self._protocol.adequacy.get(key)
        required_present = key in self._protocol.required_signal_methods
        if criteria is None or not required_present:
            return TrainingOutcome(scope, TrainingStatus.NOT_READY, "scope_protocol_incomplete")
        group_targets = {}
        for example in examples:
            group_targets.setdefault(example.patient_group_ref, set()).add(example.correctness_target)
        counts = {0: 0, 1: 0}
        for targets in group_targets.values():
            if len(targets) == 1:
                counts[next(iter(targets))] += 1
        if len(group_targets) < criteria.minimum_patient_groups:
            return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE,
                                   "patient_group_support_insufficient")
        if any(counts[target] < minimum for target, minimum in criteria.correctness_class_minimums.items()):
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
                feature = signal_by_role[role].get(self._row_key(dataset, signals, example))
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
            return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE, "training_rows_unavailable")
        return TrainingOutcome(scope, TrainingStatus.ELIGIBLE_FOR_CANDIDATE_FITTING)

    @staticmethod
    def _row_key(dataset, signals, example):
        return sha256(
            f"{signals.dataset_reference.dataset_id}\0{signals.dataset_reference.manifest_reference}\0"
            f"{prediction_fingerprint(example.prediction)}".encode("utf-8")
        ).hexdigest()

    def _train_scope(self, dataset, signals, scope, verified):
        from safira.training.features import FrozenFeatureSchema, FrozenPreprocessingState

        train_examples = tuple(row for row in dataset.development.train
                               if tuple(row.prediction.source_key) == scope.source_key)
        validation_examples = tuple(row for row in dataset.development.validation
                                    if tuple(row.prediction.source_key) == scope.source_key)
        training_feature_map = {row.row_key.value: row for row in signals.training}
        validation_feature_map = {row.row_key.value: row for row in signals.validation}
        train_features = tuple(training_feature_map[self._row_key(dataset, signals, row)] for row in train_examples)
        validation_features = tuple(validation_feature_map[self._row_key(dataset, signals, row)]
                                    for row in validation_examples)
        schema = build_feature_schema(self._protocol, scope, train_features)
        preprocessing = fit_preprocessing(self._protocol, schema, train_features)
        train_matrix = transform_rows(preprocessing, schema, train_features)
        validation_matrix = transform_rows(preprocessing, schema, validation_features)
        train_targets = tuple(row.correctness_target for row in train_examples)
        validation_targets = tuple(row.correctness_target for row in validation_examples)
        train_groups = tuple(row.patient_group_ref for row in train_examples)
        validation_groups = tuple(row.patient_group_ref for row in validation_examples)
        baseline = fit_prevalence_baseline(self._protocol, scope, train_targets,
                                           patient_group_refs=train_groups)
        logistic = fit_logistic_candidate(self._protocol, scope, train_matrix, train_targets,
                                          patient_group_refs=train_groups)
        if baseline.status is CandidateStatus.DESCRIPTIVE_ONLY:
            return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE, "training_class_support_insufficient")
        if baseline.status is not CandidateStatus.FITTED and logistic.status is not CandidateStatus.FITTED:
            return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE, "training_candidate_unavailable")
        selection = compare_candidates(self._protocol, scope, baseline, logistic, validation_matrix,
                                       validation_targets, patient_group_refs=validation_groups)
        if selection.status is SelectionStatus.NOT_READY:
            return TrainingOutcome(scope, TrainingStatus.NOT_READY, "scope_protocol_incomplete")
        if selection.status is SelectionStatus.INSUFFICIENT_EVIDENCE:
            return TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE, "candidate_comparison_insufficient")
        if selection.status is SelectionStatus.COMPARISON_UNDEFINED:
            return TrainingOutcome(scope, TrainingStatus.COMPARISON_UNDEFINED, "training_comparison_undefined")
        selected = baseline if selection.selected_family == "prevalence_baseline" else logistic
        if selected.status is not CandidateStatus.FITTED:
            return TrainingOutcome(scope, TrainingStatus.COMPARISON_UNDEFINED, "training_candidate_failed")
        train_probabilities = tuple(_candidate_probability(selected, row) for row in train_matrix)
        if any(value is None for value in train_probabilities):
            return TrainingOutcome(scope, TrainingStatus.INVALID_INPUT, "training_candidate_failed")
        training_brier = sum((p - y) ** 2 for p, y in zip(train_probabilities, train_targets)) / len(train_targets)
        dataset_reference = {
            "dataset_id": signals.dataset_reference.dataset_id,
            "manifest_reference": signals.dataset_reference.manifest_reference,
            "manifest_digest": signals.dataset_reference.manifest_digest,
            "protocol_id": signals.dataset_reference.protocol_id,
            "protocol_version": signals.dataset_reference.protocol_version,
            "builder_version": signals.dataset_reference.builder_version,
            "dataset_fingerprint": verified._input_check.dataset_fingerprint,
            "admitted_inventory_digest": sha256(json.dumps(verified._row_inventory, sort_keys=True,
                separators=(",", ":"), default=list).encode()).hexdigest(),
        }
        signal_run = {
            "run_version": signals.manifest.run_version,
            "feature_set_fingerprint": verified._input_check.feature_set_fingerprint,
            "method_ids": [[item[0], item[1], sha256(item[2].encode("utf-8")).hexdigest()]
                           for item in verified._input_check.feature_method_ids],
            "fitted_state_ids": list(verified._input_check.fitted_state_ids),
            "scope_key": list(scope.source_key),
        }
        safe_schema = schema.to_dict()
        for spec in safe_schema["feature_specs"]:
            encoded_parameters = json.dumps(spec.pop("method_parameters"), sort_keys=True,
                                            separators=(",", ":"), ensure_ascii=False)
            spec["method_parameters_sha256"] = sha256(encoded_parameters.encode("utf-8")).hexdigest()
        if selected.family == "prevalence_baseline":
            estimator_state = {"probability": selected.probability, "classes": [0, 1]}
        else:
            estimator_state = {"coefficients": list(selected.coefficients), "intercept": selected.intercept,
                               "classes": list(selected.classes)}
        logistic_config = self._protocol.logistic_configs.get(scope.source_key)
        failure_policy = self._protocol.candidate_failure_policies.get(scope.source_key)
        secondary = {family: {name: {"value": item.value, "state": item.state,
                                     "reason_code": item.reason_code}
                              for name, item in metrics.items()}
                     for family, metrics in selection.secondary_metrics.items()}
        selection_metrics = {"role": "selection_evidence", "brier_scores": dict(selection.brier_scores),
                             "secondary": secondary, "selected_family": selected.family,
                             "tie_rule": "exact_equality_prefers_prevalence_baseline",
                             "validation_spent": True, "disclosed_support": dict(selection.disclosed_support)}
        artifact = SafetyEstimatorArtifact(
            scope=scope, family=selected.family, feature_schema=safe_schema,
            preprocessing=preprocessing.to_dict(), training_protocol={
                "protocol_id": self._protocol.protocol_id, "version": self._protocol.version,
                "protocol_digest": sha256(json.dumps(self._protocol.to_dict(), sort_keys=True,
                    separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
            }, dataset_reference=dataset_reference,
            signal_run_reference=signal_run, estimator_state=estimator_state,
            candidate_configuration={"logistic": None if logistic_config is None else logistic_config.to_dict(),
                                    "candidate_failure_policy": None if failure_policy is None else failure_policy.value,
                                    "selection_metric": "brier_mean_squared_error_lower_is_better"},
            dependency_versions=dict(runtime_versions()),
            training_metrics={"role": "train", "selected_candidate_brier": training_brier},
            selection_metrics=selection_metrics,
            limitations=("uncalibrated", "non_deployable", "validation_selection_not_final_performance",
                         "future_policy_evidence_not_authorized"),
        )
        status = (TrainingStatus.SELECTED_BASELINE if selected.family == "prevalence_baseline"
                  else TrainingStatus.SELECTED_LOGISTIC)
        return TrainingOutcome(scope, status, artifact=artifact)
