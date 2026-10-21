"""Internal fixed-configuration Feature 005 candidate fitting helpers.

This module fits candidates from caller-supplied, already-admitted training
arrays only. It does not compare candidates, select a winner, publish an
artifact, or expose prediction/assessment operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import warnings

from joblib import __version__ as _joblib_version
from numpy import __version__ as _numpy_version
from scipy import __version__ as _scipy_version
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn import __version__ as _sklearn_version
from threadpoolctl import __version__ as _threadpoolctl_version

from safira.training.records import (
    CandidateFailurePolicy, LogisticCandidateConfig, TrainingProtocol, TrainingScope,
    ValidationSupportCriteria,
)


class CandidateStatus(str, Enum):
    FITTED = "FITTED"
    DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"
    NOT_READY = "NOT_READY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INVALID_INPUT = "INVALID_INPUT"
    INCOMPATIBLE_INPUT = "INCOMPATIBLE_INPUT"
    NONCONVERGED = "NONCONVERGED"
    FIT_FAILED = "FIT_FAILED"
    NONFINITE_RESULT = "NONFINITE_RESULT"


@dataclass(frozen=True)
class CandidateResult:
    scope: tuple[str, str, str]
    family: str
    status: CandidateStatus
    probability: float | None = None
    coefficients: tuple[float, ...] = ()
    intercept: float | None = None
    classes: tuple[int, ...] = ()
    C: float | None = None
    tol: float | None = None
    max_iter: int | None = None
    penalty: str = ""
    solver: str = ""
    class_weight: str | None = None
    fit_intercept: bool = True
    warm_start: bool = False
    versions: tuple[tuple[str, str], ...] = ()
    reason_code: str = ""
    protocol_id: str = ""
    protocol_version: str = ""

    def __post_init__(self):
        object.__setattr__(self, "scope", tuple(self.scope))
        object.__setattr__(self, "coefficients", tuple(self.coefficients))
        object.__setattr__(self, "classes", tuple(self.classes))
        object.__setattr__(self, "versions", tuple(self.versions))
        if len(self.scope) != 3 or type(self.status) is not CandidateStatus:
            raise ValueError("candidate_result")
        if self.probability is not None and (not math.isfinite(self.probability)
                                             or not 0.0 <= self.probability <= 1.0):
            raise ValueError("candidate_result")
        if any(not math.isfinite(value) for value in self.coefficients):
            raise ValueError("candidate_result")
        if self.intercept is not None and not math.isfinite(self.intercept):
            raise ValueError("candidate_result")


def runtime_versions() -> dict[str, str]:
    """Return only relevant numerical package versions for reproducibility."""
    return {"scikit_learn": _sklearn_version, "numpy": _numpy_version, "scipy": _scipy_version,
            "joblib": _joblib_version, "threadpoolctl": _threadpoolctl_version}


def _protocol_scope(protocol, scope):
    if type(protocol) is not TrainingProtocol or type(scope) is not TrainingScope:
        return CandidateStatus.NOT_READY, "candidate_protocol_not_ready", None
    if scope not in protocol.scopes:
        return CandidateStatus.INCOMPATIBLE_INPUT, "candidate_scope_mismatch", None
    criteria = protocol.adequacy.get(scope.source_key)
    if criteria is None:
        return CandidateStatus.NOT_READY, "candidate_group_criteria_missing", None
    return None, "", criteria


def _validate_targets(scope, targets, patient_group_refs, criteria):
    if type(scope) is not TrainingScope:
        return CandidateStatus.INCOMPATIBLE_INPUT, "candidate_scope_mismatch"
    if not isinstance(targets, (tuple, list)) or not targets or any(type(y) is not int or y not in (0, 1)
                                                                     for y in targets):
        return CandidateStatus.INVALID_INPUT, "candidate_target_invalid"
    if (not isinstance(patient_group_refs, (tuple, list)) or len(patient_group_refs) != len(targets)
            or any(type(group) is not str or not group for group in patient_group_refs)):
        return CandidateStatus.INVALID_INPUT, "candidate_group_evidence_invalid"
    group_targets = {}
    for group, target in zip(patient_group_refs, targets):
        group_targets.setdefault(group, set()).add(target)
    if len(group_targets) < criteria.minimum_patient_groups:
        return CandidateStatus.INSUFFICIENT_EVIDENCE, "candidate_group_support_insufficient"
    counts = {0: 0, 1: 0}
    for values in group_targets.values():
        if len(values) == 1:
            counts[next(iter(values))] += 1
    if any(counts[target] < minimum
           for target, minimum in criteria.correctness_class_minimums.items()):
        return CandidateStatus.INSUFFICIENT_EVIDENCE, "candidate_class_support_insufficient"
    return None, ""


def fit_prevalence_baseline(protocol, scope, targets, *, patient_group_refs):
    status, reason, criteria = _protocol_scope(protocol, scope)
    if status is not None:
        return CandidateResult(tuple(scope.source_key) if type(scope) is TrainingScope else ("", "", ""),
                               "prevalence_baseline", status, reason_code=reason)
    status, reason = _validate_targets(scope, targets, patient_group_refs, criteria)
    if status is not None:
        return CandidateResult(scope.source_key, "prevalence_baseline", status, reason_code=reason,
                               protocol_id=protocol.protocol_id, protocol_version=protocol.version)
    probability = sum(targets) / len(targets)
    status = CandidateStatus.FITTED if len(set(targets)) == 2 else CandidateStatus.DESCRIPTIVE_ONLY
    return CandidateResult(scope.source_key, "prevalence_baseline", status, probability=float(probability),
                           classes=(0, 1), reason_code="" if status is CandidateStatus.FITTED
                           else "single_class_descriptive_only", protocol_id=protocol.protocol_id,
                           protocol_version=protocol.version, versions=tuple(sorted(runtime_versions().items())))


def _matrix_status(matrix, targets):
    if not isinstance(matrix, (tuple, list)) or len(matrix) != len(targets) or not matrix:
        return "candidate_matrix_shape_invalid"
    widths = set()
    for row in matrix:
        if not isinstance(row, (tuple, list)) or not row:
            return "candidate_matrix_shape_invalid"
        widths.add(len(row))
        if any(type(value) not in (int, float) or type(value) is bool or not math.isfinite(value)
               for value in row):
            return "candidate_matrix_value_invalid"
    return None if len(widths) == 1 else "candidate_matrix_shape_invalid"


def fit_logistic_candidate(protocol, scope, matrix, targets, *, patient_group_refs):
    protocol_status, protocol_reason, criteria = _protocol_scope(protocol, scope)
    if protocol_status is not None:
        return CandidateResult(tuple(scope.source_key) if type(scope) is TrainingScope else ("", "", ""),
                               "l2_logistic", protocol_status, reason_code=protocol_reason)
    config = protocol.logistic_configs.get(scope.source_key)
    if type(config) is not LogisticCandidateConfig or not config.approved:
        return CandidateResult(scope.source_key, "l2_logistic", CandidateStatus.NOT_READY,
                               reason_code="candidate_configuration_not_approved",
                               protocol_id=protocol.protocol_id, protocol_version=protocol.version)
    status, reason = _validate_targets(scope, targets, patient_group_refs, criteria)
    if status is not None:
        return CandidateResult(scope.source_key, "l2_logistic", status, reason_code=reason,
                               protocol_id=protocol.protocol_id, protocol_version=protocol.version)
    matrix_error = _matrix_status(matrix, targets)
    if matrix_error:
        return CandidateResult(scope.source_key, "l2_logistic", CandidateStatus.INVALID_INPUT,
                               reason_code=matrix_error, protocol_id=protocol.protocol_id,
                               protocol_version=protocol.version)
    if len(set(targets)) != 2:
        return CandidateResult(scope.source_key, "l2_logistic", CandidateStatus.INSUFFICIENT_EVIDENCE,
                               reason_code="candidate_two_class_training_required",
                               protocol_id=protocol.protocol_id, protocol_version=protocol.version)
    try:
        estimator = LogisticRegression(
            penalty="l2", solver="lbfgs", C=float(config.C), tol=float(config.tol),
            max_iter=config.max_iter, class_weight=None, fit_intercept=True,
            warm_start=False, random_state=None,
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", ConvergenceWarning)
            estimator.fit(matrix, targets)
        if any(issubclass(item.category, ConvergenceWarning) for item in captured):
            return CandidateResult(scope.source_key, "l2_logistic", CandidateStatus.NONCONVERGED,
                                   C=float(config.C), tol=float(config.tol), max_iter=config.max_iter,
                                   penalty="l2", solver="lbfgs", class_weight=None,
                                   reason_code="candidate_nonconverged", protocol_id=protocol.protocol_id,
                                   protocol_version=protocol.version)
        classes = tuple(int(value) for value in estimator.classes_)
        coefficients = tuple(float(value) for value in estimator.coef_[0])
        intercept = float(estimator.intercept_[0])
        if classes != (0, 1) or not coefficients or not all(math.isfinite(v) for v in coefficients + (intercept,)):
            return CandidateResult(scope.source_key, "l2_logistic", CandidateStatus.NONFINITE_RESULT,
                                   reason_code="candidate_fitted_state_invalid", protocol_id=protocol.protocol_id,
                                   protocol_version=protocol.version)
        return CandidateResult(scope.source_key, "l2_logistic", CandidateStatus.FITTED,
                               coefficients=coefficients, intercept=intercept, classes=classes,
                               C=float(config.C), tol=float(config.tol), max_iter=config.max_iter,
                               penalty="l2", solver="lbfgs", class_weight=None,
                               fit_intercept=True, warm_start=False,
                               versions=tuple(sorted(runtime_versions().items())), protocol_id=protocol.protocol_id,
                               protocol_version=protocol.version)
    except Exception:
        return CandidateResult(scope.source_key, "l2_logistic", CandidateStatus.FIT_FAILED,
                               C=float(config.C), tol=float(config.tol), max_iter=config.max_iter,
                               penalty="l2", solver="lbfgs", class_weight=None,
                               reason_code="candidate_fit_failed", protocol_id=protocol.protocol_id,
                               protocol_version=protocol.version)


class SelectionStatus(str, Enum):
    SELECTED_BASELINE = "SELECTED_BASELINE"
    SELECTED_LOGISTIC = "SELECTED_LOGISTIC"
    COMPARISON_UNDEFINED = "COMPARISON_UNDEFINED"
    NOT_READY = "NOT_READY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class SecondaryMetric:
    value: float | None
    state: str
    reason_code: str = ""

    def __post_init__(self):
        if self.state not in ("available", "undefined"):
            raise ValueError("secondary_metric")
        if self.state == "available" and (self.value is None or not math.isfinite(self.value)):
            raise ValueError("secondary_metric")
        if self.state == "undefined" and self.value is not None:
            raise ValueError("secondary_metric")


@dataclass(frozen=True)
class CandidateSelection:
    scope: tuple[str, str, str]
    status: SelectionStatus
    selected_family: str = ""
    brier_scores: object = None
    secondary_metrics: object = None
    reason_code: str = ""
    metrics_role: str = "selection_evidence"
    validation_role: str = "selection_evidence"
    validation_spent: bool = True
    disclosed_support: object = None

    def __post_init__(self):
        from types import MappingProxyType
        object.__setattr__(self, "scope", tuple(self.scope))
        object.__setattr__(self, "brier_scores", MappingProxyType(dict(self.brier_scores or {})))
        object.__setattr__(self, "secondary_metrics", MappingProxyType({
            family: MappingProxyType(dict(metrics)) for family, metrics in (self.secondary_metrics or {}).items()}))
        support = dict(self.disclosed_support or {})
        if "correctness_class_support" in support:
            support["correctness_class_support"] = MappingProxyType(dict(support["correctness_class_support"]))
        object.__setattr__(self, "disclosed_support", MappingProxyType(support))


def _selection_failure(scope, status, reason):
    return CandidateSelection(tuple(scope.source_key), status, reason_code=reason)


def _candidate_probability(candidate, row):
    if candidate.family == "prevalence_baseline":
        value = candidate.probability
    elif candidate.family == "l2_logistic":
        if (candidate.status is not CandidateStatus.FITTED or len(candidate.coefficients) != len(row)
                or candidate.intercept is None or candidate.classes != (0, 1)):
            return None
        score = candidate.intercept + sum(coef * value for coef, value in zip(candidate.coefficients, row))
        if not math.isfinite(score):
            return None
        if score >= 0:
            value = 1.0 / (1.0 + math.exp(-score))
        else:
            exp_score = math.exp(score)
            value = exp_score / (1.0 + exp_score)
    else:
        return None
    if type(value) not in (int, float) or type(value) is bool or not math.isfinite(value) or not 0 <= value <= 1:
        return None
    return float(value)


def compare_candidates(protocol, scope, baseline, logistic, validation_matrix, targets, *, patient_group_refs):
    """Compare fixed, training-fitted candidates once on authorized validation rows."""
    if type(protocol) is not TrainingProtocol or type(scope) is not TrainingScope or scope not in protocol.scopes:
        return _selection_failure(scope, SelectionStatus.NOT_READY, "selection_protocol_not_ready")
    criteria = protocol.validation_adequacy.get(scope.source_key)
    failure_policy = protocol.candidate_failure_policies.get(scope.source_key)
    if type(criteria) is not ValidationSupportCriteria or type(failure_policy) is not CandidateFailurePolicy:
        return _selection_failure(scope, SelectionStatus.NOT_READY, "selection_criteria_not_ready")
    if (type(targets) not in (tuple, list) or not targets
            or any(type(value) is not int or value not in (0, 1) for value in targets)
            or type(patient_group_refs) not in (tuple, list) or len(patient_group_refs) != len(targets)
            or any(type(group) is not str or not group for group in patient_group_refs)):
        return _selection_failure(scope, SelectionStatus.COMPARISON_UNDEFINED, "validation_inventory_invalid")
    if (not isinstance(validation_matrix, (tuple, list)) or len(validation_matrix) != len(targets)
            or any(not isinstance(row, (tuple, list)) or not row
                   or any(type(value) not in (int, float) or type(value) is bool or not math.isfinite(value)
                          for value in row) for row in validation_matrix)
            or len({len(row) for row in validation_matrix}) != 1):
        return _selection_failure(scope, SelectionStatus.COMPARISON_UNDEFINED, "validation_matrix_invalid")
    if any(candidate.scope != scope.source_key for candidate in (baseline, logistic)):
        return _selection_failure(scope, SelectionStatus.COMPARISON_UNDEFINED, "candidate_scope_mismatch")
    if any(candidate.status in (CandidateStatus.NOT_READY, CandidateStatus.INVALID_INPUT,
                                CandidateStatus.INCOMPATIBLE_INPUT)
           for candidate in (baseline, logistic)):
        return _selection_failure(scope, SelectionStatus.NOT_READY, "candidate_failure_policy_blocked")
    group_targets = {}
    for group, target in zip(patient_group_refs, targets):
        group_targets.setdefault(group, set()).add(target)
    support = {0: 0, 1: 0}
    for values in group_targets.values():
        if len(values) == 1:
            support[next(iter(values))] += 1
    if len(group_targets) < criteria.minimum_patient_groups or any(
            support[label] < minimum for label, minimum in criteria.correctness_class_minimums.items()):
        return _selection_failure(scope, SelectionStatus.COMPARISON_UNDEFINED,
                                  "validation_class_support_insufficient")
    fitted = [candidate for candidate in (baseline, logistic) if candidate.status is CandidateStatus.FITTED]
    if len(fitted) != 2 and failure_policy is CandidateFailurePolicy.REQUIRE_ALL:
        return _selection_failure(scope, SelectionStatus.COMPARISON_UNDEFINED, "candidate_failure_policy_blocked")
    if not fitted or (baseline.status is CandidateStatus.DESCRIPTIVE_ONLY):
        return _selection_failure(scope, SelectionStatus.INSUFFICIENT_EVIDENCE, "candidate_not_comparable")
    scores = {}
    probabilities = {}
    for candidate in fitted:
        values = tuple(_candidate_probability(candidate, row) for row in validation_matrix)
        if any(value is None for value in values):
            return _selection_failure(scope, SelectionStatus.COMPARISON_UNDEFINED, "candidate_probability_invalid")
        probabilities[candidate.family] = values
        scores[candidate.family] = sum((p - y) ** 2 for p, y in zip(values, targets)) / len(targets)
    if "prevalence_baseline" in scores and "l2_logistic" in scores:
        selected = "prevalence_baseline" if scores["prevalence_baseline"] <= scores["l2_logistic"] else "l2_logistic"
    else:
        selected = next(iter(scores))
    metric_results = {}
    for family, candidate_probabilities in probabilities.items():
        if len(set(targets)) == 2:
            family_metrics = {}
            for name, function in (("auroc", roc_auc_score), ("average_precision", average_precision_score)):
                try:
                    value = float(function(targets, candidate_probabilities))
                    family_metrics[name] = SecondaryMetric(value, "available")
                except Exception:
                    family_metrics[name] = SecondaryMetric(None, "undefined", "metric_computation_undefined")
        else:
            family_metrics = {name: SecondaryMetric(None, "undefined", "validation_single_class")
                              for name in ("auroc", "average_precision")}
        metric_results[family] = family_metrics
    disclosed = {"patient_group_count": len(group_targets),
                 "correctness_class_support": {"0": support[0], "1": support[1]}} if criteria.disclose_support else {}
    return CandidateSelection(tuple(scope.source_key),
                              SelectionStatus.SELECTED_BASELINE if selected == "prevalence_baseline"
                              else SelectionStatus.SELECTED_LOGISTIC,
                              selected, scores, metric_results, disclosed_support=disclosed)
