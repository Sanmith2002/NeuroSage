from safira.calibration.verification import verify_prediction_admission
from safira.registry import ModelRegistry
from safira.signals.records import SignalSourceKey
from signals_fixtures import SyntheticSignalVerifier, make_live_record, signal_protocol


def test_exact_scope_admission_preserves_all_supported_classifier_configurations(registered_collection):
    registry, register = registered_collection
    records = []
    records.append(make_live_record(registry, register, model_id="single", labels=("binary",))[2])
    records.extend(make_live_record(registry, register, model_id="multi",
                                    labels=("label-a", "label-b"), scores=(.3, .8))[2:3])
    records.append(make_live_record(registry, register, model_id="source-a", labels=("shared",))[2])
    records.append(make_live_record(registry, register, model_id="source-b", labels=("shared",), scores=(.9,))[2])
    records.append(make_live_record(registry, register, model_id="versioned", version="v1",
                                    labels=("same-label",))[2])
    records.append(make_live_record(registry, register, model_id="versioned", version="v2",
                                    labels=("same-label",), scores=(.6,))[2])

    accepted = []
    for record in records:
        verifier = SyntheticSignalVerifier()
        verifier.admit(record)
        protocol = signal_protocol(record.source_key, {"evidence_coverage": {"required_evidence": []}})
        check = verify_prediction_admission(registry, protocol, verifier, record)
        assert check.source_key == record.source_key
        accepted.append(SignalSourceKey(*record.source_key))
    assert accepted[0] != accepted[1]
    assert accepted[2].label_id == accepted[3].label_id == "shared"
    assert accepted[2] != accepted[3]
    assert accepted[4].model_id == accepted[5].model_id == "versioned"
    assert accepted[4].model_version != accepted[5].model_version


def _service_case(registered_collection, *, baseline=False, unavailable=False,
                  transformation_unavailable=False, model_id="training-model"):
    from dataclasses import replace
    from test_training_acceptance import _make_service
    from test_calibration_bundle_gate import OriginLedger
    from training_fixtures import training_scope
    from safira.calibration.records import CalibrationProtocol
    from safira.calibration.service import CalibrationService

    partitions = {
        "train": (("t1", 0), ("t2", 0), ("t3", 1), ("t4", 1)),
        "validation": (("v1", 0), ("v2", 1), ("v3", 0), ("v4", 1)),
        "calibration": (("c1", 0), ("c2", 1), ("c3", 0), ("c4", 1),
                        ("c5", 0), ("c6", 1)),
    }
    validation_values = (0.0, 0.0, 0.0, 0.0) if baseline else (0.0, 1.0, 0.0, 1.0)
    registry, dataset, signals, training_protocol, ledger, training_service = _make_service(
        registered_collection, model_id=model_id, partitions=partitions, validation_values=validation_values,
    )
    # Scores are synthetic, admitted evidence. They overlap across target classes
    # while retaining a positive association so the approved logistic MLE is finite.
    values = (0.0, 2.0, 3.0, 4.0, 1.0, 5.0)
    calibration = tuple(replace(row, predictors=(replace(row.predictors[0], value=values[index]),))
                        for index, row in enumerate(signals.calibration))
    if unavailable:
        calibration = (replace(calibration[0], predictors=()), *calibration[1:])
    if transformation_unavailable:
        from safira.signals.base import SignalState
        first = calibration[0]
        missing = replace(first.predictors[0], state=SignalState.MISSING, value=None,
                          reason_code="evidence_missing")
        calibration = (replace(first, predictors=(missing,)), *calibration[1:])
        from safira.training.records import FeaturePolicy
        scope = training_protocol.scopes[0]
        prior = training_protocol.feature_policies[scope.source_key].features[0]
        updated = replace(prior, state_indicators=True, allowed_nonvalue_states=("missing",))
        training_protocol = replace(training_protocol, feature_policies={scope.source_key:
            FeaturePolicy((updated,))})
        from safira.training.service import SafetyTrainingService
        training_service = SafetyTrainingService(registry, training_protocol, ledger)
    signals = replace(signals, calibration=calibration)
    ledger.admit(dataset, signals, signals.dataset_reference)
    training_outcomes = training_service.train(dataset, signals)
    base_artifacts = {item.scope.source_key: item.artifact for item in training_outcomes
                      if item.artifact is not None}
    assert len(base_artifacts) == 1
    base = next(iter(base_artifacts.values()))
    origin = OriginLedger(ledger)
    origin.admit_artifact(base)
    scope = training_scope(registry, base.scope.model_id, base.scope.model_version, base.scope.label_id)
    configuration = {"method_version": "logistic_recalibration_v1",
        "support_by_scope": {"\0".join(scope.source_key): {
            "minimum_patient_groups": 4, "correctness_class_minimums": {"0": 1, "1": 1}}},
        "selected_artifacts_by_scope": {"\0".join(scope.source_key): {
            "artifact_version": base.artifact_version, "family": base.family}},
        "logistic_settings_by_scope": {"\0".join(scope.source_key): {
            "tol": 1e-8, "max_iter": 1000, "solver": "lbfgs", "penalty": None,
            "fit_intercept": True, "class_weight": None, "warm_start": False,
            "occurrence_weighting": "unit_per_occurrence",
            "convergence_criterion": "warning_and_iteration_limit_v1",
            "deterministic_expectation": "same_environment_repeat_v1",
            "score_identifiability_criterion": "intercept_plus_score_full_rank_v1",
            "separation_criterion": "scalar_range_ordering_v1", "slope_rule": "strictly_positive"}}}
    protocol = CalibrationProtocol("calibration-protocol", "v1", (scope,), configuration,
        required_settings=tuple(configuration))
    service = CalibrationService(registry, protocol, origin)
    return registry, dataset, signals, base_artifacts, service, origin, base.family


def test_public_service_fits_exact_scope_and_emits_non_deployable_artifact(registered_collection):
    from safira.calibration.records import CalibrationStatus

    registry, dataset, signals, artifacts, service, _, family = _service_case(registered_collection)
    assert family == "l2_logistic"
    outcomes = service.calibrate(dataset, signals, artifacts)
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED
    assert outcome.artifact is not None
    assert outcome.artifact.base_family == family
    assert outcome.artifact.lifecycle["protected_test_accessed"] is False
    assert outcome.artifact.lifecycle["non_deployable"] is True
    exported = str(outcome.to_dict()) + repr(outcome)
    assert not any(f"'{value}'" in exported for value in ("c1", "c2", "c3", "c4", "c5", "c6"))
    repeated = service.calibrate(dataset, signals, artifacts)[0]
    assert repeated.artifact.digest == outcome.artifact.digest


def test_public_service_supports_prevalence_base_and_constant_mapping(registered_collection):
    from safira.calibration.records import CalibrationStatus

    registry, dataset, signals, artifacts, service, origin, _ = _service_case(registered_collection, baseline=True)
    # If selection does not choose the baseline for this fixed synthetic validation
    # fixture, the test fails with the observed family rather than disguising it.
    base = next(iter(artifacts.values()))
    assert base.family == "prevalence_baseline"
    outcomes = service.calibrate(dataset, signals, artifacts)
    assert outcomes[0].status is CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED
    assert outcomes[0].artifact.mapping["constant_output"] is True
    assert outcomes[0].artifact.mapping["no_individualized_discrimination"] is True


def test_required_aligned_evidence_missing_returns_scope_local_unavailable(registered_collection):
    from safira.calibration.records import CalibrationStatus

    registry, dataset, signals, artifacts, service, _, _ = _service_case(
        registered_collection, unavailable=True)
    outcomes = service.calibrate(dataset, signals, artifacts)
    assert len(outcomes) == 1
    assert outcomes[0].status is CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE
    assert outcomes[0].artifact is None


def test_frozen_transformation_unavailability_short_circuits_only_its_scope(registered_collection):
    from safira.calibration.records import CalibrationStatus
    from safira.calibration.verification import _evaluate_scope_readiness

    registry, dataset, signals, artifacts, service, _, _ = _service_case(
        registered_collection, transformation_unavailable=True)
    artifact = next(iter(artifacts.values()))
    scope = artifact.scope
    assert _evaluate_scope_readiness(dataset, signals, artifact, scope, service._protocol).status is None
    outcome = service.calibrate(dataset, signals, artifacts)[0]
    assert outcome.status is CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE
    assert outcome.artifact is None


def test_multi_label_scopes_remain_independent_with_one_ineligible_scope(registered_collection):
    from dataclasses import replace
    from test_training_acceptance import _make_service
    from test_calibration_bundle_gate import OriginLedger
    from training_fixtures import training_scope
    from safira.calibration.records import CalibrationProtocol, CalibrationStatus
    from safira.calibration.service import CalibrationService

    partitions = {
        "train": tuple((f"t{i}", (i // 2) % 2) for i in range(8)),
        "validation": tuple((f"v{i}", (i // 2) % 2) for i in range(8)),
        "calibration": tuple((f"c{i}", (i // 2) % 2) for i in range(12)),
    }
    registry, dataset, signals, training_protocol, ledger, training_service = _make_service(
        registered_collection, labels=("label-a", "label-b"), partitions=partitions,
        validation_values=tuple(float((i // 2) % 2) for i in range(8)))
    per_label = (0.0, 2.0, 3.0, 4.0, 1.0, 5.0)
    values = tuple(value for value in per_label for _ in range(2))
    signals = replace(signals, calibration=tuple(
        replace(row, predictors=(replace(row.predictors[0], value=values[i]),))
        for i, row in enumerate(signals.calibration)))
    ledger.admit(dataset, signals, signals.dataset_reference)
    base = {item.scope.source_key: item.artifact for item in training_service.train(dataset, signals)
            if item.artifact is not None}
    assert len(base) == 2
    origin = OriginLedger(ledger)
    for item in base.values():
        origin.admit_artifact(item)
    scopes = tuple(training_scope(registry, "training-model", "v1", label)
                   for label in ("label-a", "label-b"))
    config = {"method_version": "logistic_recalibration_v1",
        "support_by_scope": {"\0".join(s.source_key): {"minimum_patient_groups": 1,
            "correctness_class_minimums": {}} for s in scopes},
        "selected_artifacts_by_scope": {"\0".join(s.source_key): {
            "artifact_version": base[s.source_key].artifact_version,
            "family": base[s.source_key].family} for s in scopes},
        "logistic_settings_by_scope": {"\0".join(s.source_key): {
            "tol": 1e-8, "max_iter": 1000, "solver": "lbfgs", "penalty": None,
            "fit_intercept": True, "class_weight": None, "warm_start": False,
            "occurrence_weighting": "unit_per_occurrence",
            "convergence_criterion": "warning_and_iteration_limit_v1",
            "deterministic_expectation": "same_environment_repeat_v1",
            "score_identifiability_criterion": "intercept_plus_score_full_rank_v1",
            "separation_criterion": "scalar_range_ordering_v1", "slope_rule": "strictly_positive"}
            for s in scopes}}
    config["support_by_scope"]["\0".join(scopes[1].source_key)] = {
        "minimum_patient_groups": 20, "correctness_class_minimums": {}}
    protocol = CalibrationProtocol("multi-calibration", "v1", scopes, config,
                                   required_settings=tuple(config))
    outcomes = CalibrationService(registry, protocol, origin).calibrate(dataset, signals, base)
    assert tuple(item.scope.source_key for item in outcomes) == tuple(sorted(s.source_key for s in scopes))
    by_scope = {item.scope.label_id: item for item in outcomes}
    assert by_scope["label-b"].status is CalibrationStatus.INSUFFICIENT_EVIDENCE
    assert by_scope["label-b"].artifact is None
    # The independent scope either fits or reports its own numerical feasibility;
    # it is not overwritten by the label-b support deficiency.
    assert by_scope["label-a"].status is CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED


def test_independent_contributors_with_overlapping_label_keep_separate_outcomes(registered_collection):
    from test_training_acceptance import _make_multi_model_service
    from test_calibration_bundle_gate import OriginLedger
    from safira.calibration.records import CalibrationProtocol, CalibrationStatus
    from safira.calibration.service import CalibrationService

    dataset, signals, training_protocol, trainer = _make_multi_model_service(registered_collection)
    registry = registered_collection[0]
    ledger = trainer._verifier
    base = {item.scope.source_key: item.artifact for item in trainer.train(dataset, signals)
            if item.artifact is not None}
    assert len(base) == 2
    origin = OriginLedger(ledger)
    for item in base.values():
        origin.admit_artifact(item)
    scopes = tuple(base[key].scope for key in sorted(base))
    configuration = {"method_version": "logistic_recalibration_v1",
        "support_by_scope": {"\0".join(scope.source_key): {"minimum_patient_groups": 1,
            "correctness_class_minimums": {}} for scope in scopes},
        "selected_artifacts_by_scope": {"\0".join(scope.source_key): {
            "artifact_version": base[scope.source_key].artifact_version,
            "family": base[scope.source_key].family} for scope in scopes}}
    protocol = CalibrationProtocol("contributors", "v1", scopes, configuration,
                                   required_settings=tuple(configuration))
    outcomes = CalibrationService(registry, protocol, origin).calibrate(dataset, signals, base)
    assert len(outcomes) == 2
    assert len({item.scope.model_id for item in outcomes}) == 2
    assert {item.scope.label_id for item in outcomes} == {"shared-label"}
    assert all(item.status is CalibrationStatus.INSUFFICIENT_EVIDENCE for item in outcomes)
    assert all(item.artifact is None for item in outcomes)


def test_signal_run_ledger_requires_exact_previously_admitted_content(registered_collection):
    from dataclasses import replace
    import pytest
    from calibration_ledgers import SignalRunLedger
    from training_fixtures import build_inputs

    registry, register = registered_collection
    _, _, signals, _ = build_inputs(registry, register)
    ledger = SignalRunLedger()
    with pytest.raises(ValueError):
        ledger.verify(signals)
    ledger.admit(signals)
    ledger.verify(signals)
    changed = replace(signals, cohort_support={"synthetic": "changed"})
    with pytest.raises(ValueError):
        ledger.verify(changed)
