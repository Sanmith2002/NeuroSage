"""Private numerical methods for Feature 006 Batch B.

All fit inputs are occurrence-weighted and arise from the Feature 006 verified
bundle. This module does not publish artifacts, service results, or predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log, log1p
from types import MappingProxyType

from safira.calibration.records import CalibrationStatus
from safira.training.records import TrainingScope


@dataclass(frozen=True, repr=False)
class _FitVectors:
    scores: tuple[float, ...]
    targets: tuple[int, ...]
    patient_group_refs: tuple[str, ...]
    unique_patient_groups: int
    correctness_class_support: tuple[int, int]

    def __post_init__(self):
        object.__setattr__(self, "scores", tuple(self.scores))
        object.__setattr__(self, "targets", tuple(self.targets))
        object.__setattr__(self, "patient_group_refs", tuple(self.patient_group_refs))
        if (len(self.scores) != len(self.targets) or len(self.targets) != len(self.patient_group_refs)
                or any(type(y) is not int or y not in (0, 1) for y in self.targets)
                or any(type(z) not in (int, float) or type(z) is bool or not isfinite(z) for z in self.scores)
                or any(type(group) is not str or not group for group in self.patient_group_refs)):
            raise ValueError("fit_vectors")


@dataclass(frozen=True, repr=False)
class _MappingFit:
    status: CalibrationStatus | None
    reason_code: str
    intercept: float | None = None
    slope: float | None = None
    offset: float | None = None
    constant_probability: float | None = None
    iterations: int | None = None
    solver: str = ""
    penalty: str | None = None


def _separation_check(scores, targets):
    """Exact scalar range-separation test, after class and rank checks."""
    scores, targets = tuple(scores), tuple(targets)
    if len(scores) != len(targets) or not scores:
        return "class_missing"
    if (any(type(z) not in (int, float) or type(z) is bool or not isfinite(z) for z in scores)
            or any(type(y) is not int or y not in (0, 1) for y in targets)):
        return "nonfinite"
    z0 = [float(z) for z, y in zip(scores, targets) if y == 0]
    z1 = [float(z) for z, y in zip(scores, targets) if y == 1]
    if not z0 or not z1:
        return "class_missing"
    if len(set(scores)) < 2:
        return "rank_deficient"
    if max(z0) <= min(z1) or max(z1) <= min(z0):
        return "separated"
    return None


def _build_fit_vectors(verified_inputs, scope: TrainingScope, score_result):
    """Create exact-scope ephemeral occurrence vectors from an admitted token."""
    from hashlib import sha256
    from safira.calibration.verification import _VerifiedCalibrationInputs, _prediction_fingerprint
    from safira.calibration.scores import _ScoreReconstruction
    from safira.dataset.records import CorrectnessExample

    if (type(verified_inputs) is not _VerifiedCalibrationInputs or type(scope) is not TrainingScope
            or type(score_result) is not _ScoreReconstruction or score_result.status is not None
            or scope.source_key not in verified_inputs.readiness
            or verified_inputs.readiness[scope.source_key].status is not None):
        raise ValueError("fit_admission")
    dataset = verified_inputs._dataset
    signals = verified_inputs._signals
    examples = [item for item in dataset.development.calibration
                if type(item) is CorrectnessExample and item.partition_role == "calibration"
                and tuple(item.prediction.source_key) == scope.source_key]
    rows = [item for item in signals.calibration if item.source_key.to_tuple() == scope.source_key]
    artifact = verified_inputs._artifacts[scope.source_key]
    if (score_result.artifact_digest != artifact.digest or score_result.source_key != scope.source_key
            or score_result.row_keys != tuple(row.row_key.value for row in rows)):
        raise ValueError("score_provenance")
    def key_for_prediction(prediction):
        value = sha256(f"{signals.dataset_reference.dataset_id}\0{signals.dataset_reference.manifest_reference}\0"
                       f"{_prediction_fingerprint(prediction)}".encode()).hexdigest()
        return value
    expected = {key_for_prediction(example.prediction): example for example in examples}
    actual = {row.row_key.value: row for row in rows}
    if (len(expected) != len(examples) or len(actual) != len(rows) or set(actual) != set(expected)
            or len(score_result.scores) != len(rows)):
        raise ValueError("fit_alignment")
    # `_reconstruct_scores` returns scores in the same order as its rows. Map by
    # opaque row key before constructing the target sequence.
    score_by_key = dict(zip((row.row_key.value for row in rows), score_result.scores))
    ordered_keys = sorted(expected)
    ordered_examples = [expected[key] for key in ordered_keys]
    ordered_scores = tuple(score_by_key[key] for key in ordered_keys)
    targets = tuple(example.correctness_target for example in ordered_examples)
    groups = tuple(example.patient_group_ref for example in ordered_examples)
    group_targets = {}
    for group, target in zip(groups, targets):
        group_targets.setdefault(group, set()).add(target)
    class_support = [0, 0]
    for values in group_targets.values():
        if len(values) == 1:
            class_support[next(iter(values))] += 1
    return _FitVectors(ordered_scores, targets, groups, len(group_targets), tuple(class_support))


def _fit_logistic(scores, targets, *, tol: float, max_iter: int) -> _MappingFit:
    """Fit only unpenalized q=sigmoid(a+b*z), without fallback or retry."""
    import warnings
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression

    scores, targets = tuple(scores), tuple(targets)
    if (len(scores) != len(targets) or not scores
            or any(type(z) not in (int, float) or type(z) is bool or not isfinite(z) for z in scores)
            or any(type(y) is not int or y not in (0, 1) for y in targets)):
        return _MappingFit(CalibrationStatus.INVALID_INPUT, "input_invalid")
    if type(tol) not in (int, float) or type(tol) is bool or not isfinite(tol) or tol <= 0:
        return _MappingFit(CalibrationStatus.NOT_READY, "approval_missing")
    if type(max_iter) is not int or max_iter < 1:
        return _MappingFit(CalibrationStatus.NOT_READY, "approval_missing")
    geometry = _separation_check(scores, targets)
    if geometry in ("class_missing",):
        return _MappingFit(CalibrationStatus.INSUFFICIENT_EVIDENCE, "support_insufficient")
    if geometry is not None:
        return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure")
    estimator = LogisticRegression(
        penalty=None, solver="lbfgs", fit_intercept=True, class_weight=None,
        warm_start=False, tol=float(tol), max_iter=max_iter,
    )
    try:
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always", ConvergenceWarning)
            estimator.fit([[float(z)] for z in scores], list(targets),
                          sample_weight=[1.0] * len(scores))
        if any(issubclass(item.category, ConvergenceWarning) for item in seen):
            return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure",
                               solver="lbfgs", penalty=None)
        iterations = int(estimator.n_iter_[0])
        if iterations >= max_iter:
            return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure",
                               iterations=iterations, solver="lbfgs", penalty=None)
        if tuple(int(value) for value in estimator.classes_) != (0, 1):
            return _MappingFit(CalibrationStatus.INVALID_INPUT, "input_invalid")
        intercept, slope = float(estimator.intercept_[0]), float(estimator.coef_[0][0])
        if not isfinite(intercept) or not isfinite(slope):
            return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure")
        if slope <= 0:
            return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure",
                               intercept=intercept, slope=slope, iterations=iterations,
                               solver="lbfgs", penalty=None)
        return _MappingFit(None, "", intercept=intercept, slope=slope,
                           iterations=iterations, solver="lbfgs", penalty=None)
    except Exception:
        return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure",
                           solver="lbfgs", penalty=None)


def _fit_baseline(vectors: _FitVectors, p0: float) -> _MappingFit:
    """Fit exactly one constant prevalence offset with unit occurrence weights."""
    if type(vectors) is not _FitVectors:
        return _MappingFit(CalibrationStatus.INVALID_INPUT, "input_invalid")
    if (type(p0) not in (int, float) or type(p0) is bool or not isfinite(p0)
            or not 0.0 < p0 < 1.0):
        return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure")
    if not vectors.targets or 0 not in vectors.targets or 1 not in vectors.targets:
        return _MappingFit(CalibrationStatus.INSUFFICIENT_EVIDENCE, "support_insufficient")
    p_cal = sum(vectors.targets) / len(vectors.targets)
    try:
        offset = (log(p_cal) - log1p(-p_cal)) - (log(float(p0)) - log1p(-float(p0)))
    except (ValueError, OverflowError):
        return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure")
    if not isfinite(offset):
        return _MappingFit(CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure")
    return _MappingFit(None, "", offset=offset, constant_probability=p_cal)


def _fit_scope_mapping(verified_inputs, scope, score_result, protocol):
    """Private exact-family dispatcher; returns mapping values only."""
    from safira.calibration.records import CalibrationProtocol
    from safira.calibration.scores import _ScoreReconstruction
    from safira.calibration.verification import _VerifiedCalibrationInputs

    if (type(verified_inputs) is not _VerifiedCalibrationInputs or type(scope) is not TrainingScope
            or type(score_result) is not _ScoreReconstruction or type(protocol) is not CalibrationProtocol
            or protocol is not verified_inputs._protocol or not protocol.ready):
        return _MappingFit(CalibrationStatus.NOT_READY, "approval_missing")
    artifact = verified_inputs._artifacts.get(scope.source_key)
    readiness = verified_inputs.readiness.get(scope.source_key)
    if artifact is None or readiness is None or readiness.status is not None or artifact.scope != scope:
        return _MappingFit(CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    if score_result.status is not None:
        return _MappingFit(score_result.status, score_result.reason_code)
    try:
        vectors = _build_fit_vectors(verified_inputs, scope, score_result)
    except Exception:
        return _MappingFit(CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    if artifact.family == "prevalence_baseline":
        return _fit_baseline(vectors, artifact.estimator_state["probability"])
    if artifact.family != "l2_logistic":
        return _MappingFit(CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    settings_by_scope = protocol.configuration.get("logistic_settings_by_scope", {})
    settings = settings_by_scope.get("\0".join(scope.source_key)) if hasattr(settings_by_scope, "get") else None
    required = {"tol", "max_iter", "solver", "penalty", "fit_intercept", "class_weight",
                "warm_start", "occurrence_weighting", "convergence_criterion",
                "deterministic_expectation", "score_identifiability_criterion",
                "separation_criterion", "slope_rule"}
    if not hasattr(settings, "get") or not required <= set(settings):
        return _MappingFit(CalibrationStatus.NOT_READY, "approval_missing")
    if (settings["solver"] != "lbfgs" or settings["penalty"] is not None
            or settings["fit_intercept"] is not True or settings["class_weight"] is not None
            or settings["warm_start"] is not False
            or settings["occurrence_weighting"] != "unit_per_occurrence"
            or settings["convergence_criterion"] != "warning_and_iteration_limit_v1"
            or settings["deterministic_expectation"] != "same_environment_repeat_v1"
            or settings["score_identifiability_criterion"] != "intercept_plus_score_full_rank_v1"
            or settings["separation_criterion"] != "scalar_range_ordering_v1"
            or settings["slope_rule"] != "strictly_positive"):
        return _MappingFit(CalibrationStatus.NOT_READY, "approval_missing")
    return _fit_logistic(vectors.scores, vectors.targets,
                         tol=settings["tol"], max_iter=settings["max_iter"])


