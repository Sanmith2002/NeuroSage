"""Internal occurrence-vector and fit-dispatch invariants (synthetic only)."""

from dataclasses import replace

from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
from safira.calibration.verification import _verify_bundle
from test_calibration_bundle_gate import setup
from test_calibration_scores import _parameters_from_signals


def _admitted(registered_collection):
    registry, dataset, signals, artifact, scope, protocol, verifier = setup(registered_collection)
    token = _verify_bundle(registry, dataset, signals, {scope.source_key: artifact}, protocol, verifier)
    state = _reconstruct_feature_state(artifact, _parameters_from_signals(signals))
    rows = tuple(row for row in signals.calibration if row.source_key.to_tuple() == scope.source_key)
    scores = _reconstruct_scores(state, rows)
    return token, scope, scores


def test_occurrence_vectors_preserve_repeats_but_keep_support_ids_separate(registered_collection):
    from safira.calibration.fitting import _build_fit_vectors
    token, scope, scores = _admitted(registered_collection)
    vectors = _build_fit_vectors(token, scope, scores)
    assert len(vectors.scores) == len(vectors.targets) == 2
    assert set(vectors.targets) == {0, 1}
    assert vectors.unique_patient_groups == 2
    assert vectors.correctness_class_support == (1, 1)
    assert len(vectors.patient_group_refs) == 2
    assert not hasattr(vectors, "predictors")


def test_occurrence_vector_builder_rejects_unadmitted_or_ineligible_scope(registered_collection):
    import pytest
    from safira.calibration.fitting import _build_fit_vectors
    token, scope, scores = _admitted(registered_collection)
    with pytest.raises(ValueError):
        _build_fit_vectors(object(), scope, scores)
    with pytest.raises(ValueError):
        _build_fit_vectors(token, scope, replace_status(scores))
    with pytest.raises(ValueError):
        _build_fit_vectors(token, scope, replace(scores, artifact_digest="0" * 64))


def replace_status(result):
    from dataclasses import replace
    from safira.calibration.records import CalibrationStatus
    return replace(result, status=CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE, scores=())


def test_fitting_inputs_exclude_train_and_validation_and_do_not_mutate_artifact(registered_collection):
    from safira.calibration.fitting import _build_fit_vectors, _fit_baseline
    token, scope, scores = _admitted(registered_collection)
    artifact = token._artifacts[scope.source_key]
    before = artifact.to_dict()
    vectors = _build_fit_vectors(token, scope, scores)
    from hashlib import sha256
    from safira.calibration.verification import _prediction_fingerprint
    examples = [row for row in token._dataset.development.calibration
                if row.prediction.source_key == scope.source_key]
    examples.sort(key=lambda row: sha256(
        f"{token._signals.dataset_reference.dataset_id}\0{token._signals.dataset_reference.manifest_reference}\0"
        f"{_prediction_fingerprint(row.prediction)}".encode()).hexdigest())
    assert vectors.targets == tuple(row.correctness_target for row in examples)
    assert len(vectors.targets) == len(examples)
    _fit_baseline(vectors, .5)
    assert artifact.to_dict() == before


def test_repeated_visits_are_occurrences_but_one_patient_for_support(registered_collection):
    from safira.calibration.records import CalibrationProtocol
    from safira.calibration.fitting import _build_fit_vectors
    from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
    from test_calibration_bundle_gate import OriginLedger
    from test_training_acceptance import _make_service
    from safira.training.service import SafetyTrainingService
    from tests.training_fixtures import SyntheticTrainingLedger
    from signals_fixtures import SyntheticSignalVerifier
    from training_fixtures import training_scope
    partitions = {
        "train": (("t1", 0), ("t2", 0), ("t3", 1), ("t4", 1)),
        "validation": (("v1", 0), ("v2", 1), ("v3", 0), ("v4", 1)),
        "calibration": (("repeat", 0), ("repeat", 0), ("other", 1)),
    }
    registry, dataset, signals, _, ledger, service = _make_service(
        registered_collection, partitions=partitions)
    artifact = service.train(dataset, signals)[0].artifact
    origin = OriginLedger(ledger)
    origin.admit_artifact(artifact)
    scope = training_scope(registry, artifact.scope.model_id, artifact.scope.model_version,
                           artifact.scope.label_id)
    key = "\0".join(scope.source_key)
    protocol = CalibrationProtocol("calibration", "repeat-v1", (scope,),
        {"method_version": "logistic_recalibration_v1", "support_by_scope": {key: {
            "minimum_patient_groups": 2, "correctness_class_minimums": {"0": 1, "1": 1}}},
         "selected_artifacts_by_scope": {key: {"artifact_version": artifact.artifact_version,
                                                "family": artifact.family}}},
        required_settings=("method_version", "support_by_scope", "selected_artifacts_by_scope"))
    token = _verify_bundle(registry, dataset, signals, {scope.source_key: artifact}, protocol, origin)
    state = _reconstruct_feature_state(artifact, _parameters_from_signals(signals))
    rows = tuple(row for row in signals.calibration if row.source_key.to_tuple() == scope.source_key)
    scores = _reconstruct_scores(state, rows)
    vectors = _build_fit_vectors(token, scope, scores)
    assert len(vectors.targets) == 3
    assert vectors.unique_patient_groups == 2
    assert vectors.correctness_class_support == (1, 1)
    assert vectors.patient_group_refs.count("repeat") == 2


def test_fixed_internal_fit_depends_only_on_calibration_vectors_and_no_identifiers():
    from safira.calibration.fitting import _FitVectors, _fit_baseline, _fit_logistic
    first = _FitVectors((.2, .2, .2, .2), (0, 0, 1, 1), ("g1", "g1", "g2", "g3"), 3, (1, 2))
    second = _FitVectors((.2, .2, .2, .2), (0, 1, 1, 1), ("g4", "g5", "g5", "g6"), 3, (1, 2))
    fit_a = _fit_baseline(first, .25)
    fit_b = _fit_baseline(second, .25)
    assert fit_a.constant_probability == .5
    assert fit_b.constant_probability == .75
    assert fit_a.offset != fit_b.offset
    fit_signature = __import__("inspect").signature(_fit_logistic)
    assert set(fit_signature.parameters) == {"scores", "targets", "tol", "max_iter"}
    assert not hasattr(first, "predictors")


def test_dispatcher_requires_the_exact_admitted_bundle_protocol_and_selected_family(registered_collection):
    from safira.calibration.fitting import _fit_scope_mapping
    from safira.calibration.records import CalibrationStatus
    token, scope, scores = _admitted(registered_collection)
    result = _fit_scope_mapping(token, scope, scores, token._protocol)
    artifact = token._artifacts[scope.source_key]
    if artifact.family == "prevalence_baseline":
        assert result.status is None
        assert result.slope is None
        assert result.constant_probability is not None
    else:
        assert result.status is CalibrationStatus.NOT_READY
    assert _fit_scope_mapping(token, scope, scores, object()).status is CalibrationStatus.NOT_READY
    assert _fit_scope_mapping(object(), scope, scores, token._protocol).status is CalibrationStatus.NOT_READY


def test_logistic_dispatch_uses_only_preapproved_exact_scope_numerics(registered_collection):
    from safira.calibration.fitting import _fit_scope_mapping
    from safira.calibration.records import CalibrationProtocol, CalibrationStatus
    from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
    from safira.calibration.verification import _verify_bundle
    from test_calibration_bundle_gate import OriginLedger
    from test_training_acceptance import _make_service
    from safira.training.service import SafetyTrainingService
    from tests.training_fixtures import SyntheticTrainingLedger
    from signals_fixtures import SyntheticSignalVerifier
    from training_fixtures import training_scope
    partitions = {"train": (("t1", 0), ("t2", 0), ("t3", 1), ("t4", 1)),
                  "validation": (("v1", 1), ("v2", 0), ("v3", 1), ("v4", 0)),
                  "calibration": (("c1", 0), ("c2", 0), ("c3", 0), ("c4", 1), ("c5", 1))}
    registry, dataset, signals, training_protocol, _, _ = _make_service(
        registered_collection, validation_values=(1., 0., 1., 0.),
        train_values=(.05, .10, .90, .95), partitions=partitions)
    calibration_values = (0., 1., 2., 1., 1.5)
    rows = tuple(replace(row, predictors=(replace(row.predictors[0], value=calibration_values[index]),))
                 for index, row in enumerate(signals.calibration))
    signals = replace(signals, calibration=rows)
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, signals.dataset_reference)
    service = SafetyTrainingService(registry, training_protocol, ledger)
    artifact = service.train(dataset, signals)[0].artifact
    assert artifact.family == "l2_logistic"
    origin = OriginLedger(ledger)
    origin.admit_artifact(artifact)
    scope = training_scope(registry, artifact.scope.model_id, artifact.scope.model_version,
                           artifact.scope.label_id)
    key = "\0".join(scope.source_key)
    config = {"method_version": "logistic_recalibration_v1", "support_by_scope": {key: {
        "minimum_patient_groups": 1, "correctness_class_minimums": {}}},
        "selected_artifacts_by_scope": {key: {"artifact_version": artifact.artifact_version,
                                               "family": artifact.family}},
        "logistic_settings_by_scope": {key: {"tol": 1e-8, "max_iter": 1000,
            "solver": "lbfgs", "penalty": None, "fit_intercept": True,
            "class_weight": None, "warm_start": False,
            "occurrence_weighting": "unit_per_occurrence",
            "convergence_criterion": "warning_and_iteration_limit_v1",
            "deterministic_expectation": "same_environment_repeat_v1",
            "score_identifiability_criterion": "intercept_plus_score_full_rank_v1",
            "separation_criterion": "scalar_range_ordering_v1", "slope_rule": "strictly_positive"}}}
    required = ("method_version", "support_by_scope", "selected_artifacts_by_scope",
                "logistic_settings_by_scope")
    protocol = CalibrationProtocol("calibration", "logistic-v1", (scope,), config,
                                   required_settings=required)
    token = _verify_bundle(registry, dataset, signals, {scope.source_key: artifact}, protocol, origin)
    state = _reconstruct_feature_state(artifact, _parameters_from_signals(signals))
    rows = tuple(row for row in signals.calibration if row.source_key.to_tuple() == scope.source_key)
    scores = _reconstruct_scores(state, rows)
    fitted = _fit_scope_mapping(token, scope, scores, protocol)
    assert fitted.status is None and fitted.slope > 0

    incomplete = dict(config)
    incomplete["logistic_settings_by_scope"] = {key: {"tol": 1e-8, "max_iter": 1000,
        "solver": "lbfgs", "penalty": None, "fit_intercept": True,
        "class_weight": None, "warm_start": False,
        "occurrence_weighting": "unit_per_occurrence",
        "convergence_criterion": "warning_and_iteration_limit_v1",
        "deterministic_expectation": "same_environment_repeat_v1",
        "separation_criterion": "scalar_range_ordering_v1", "slope_rule": "strictly_positive"}}
    not_ready = CalibrationProtocol("calibration", "logistic-incomplete", (scope,), incomplete,
                                    required_settings=required)
    incomplete_token = _verify_bundle(registry, dataset, signals, {scope.source_key: artifact},
                                      not_ready, origin)
    assert _fit_scope_mapping(incomplete_token, scope, scores, not_ready).status is CalibrationStatus.NOT_READY
