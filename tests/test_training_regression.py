def test_training_never_invokes_primary_prediction_signal_extraction_target_building_or_assessment(
        registered_collection, monkeypatch):
    from safira.collection.live import collect_live
    from safira.dataset.builder import DatasetBuilder
    from safira.models.assessment import SafetyAssessment
    from safira.signals.service import SignalExtractor
    from safira.training.records import TrainingStatus
    from test_training_acceptance import _make_service

    registry, dataset, signals, _, _, service = _make_service(registered_collection)
    def forbidden(*_args, **_kwargs):
        raise AssertionError("out-of-scope API invoked")
    monkeypatch.setattr(DatasetBuilder, "build", forbidden)
    monkeypatch.setattr(SignalExtractor, "extract_record", forbidden)
    monkeypatch.setattr(SignalExtractor, "build_feature_set", forbidden)
    monkeypatch.setattr(SignalExtractor, "apply_protected", forbidden)
    monkeypatch.setattr("safira.collection.live.collect_live", forbidden)
    monkeypatch.setattr("safira.models.assessment.SafetyAssessment", forbidden)
    monkeypatch.setattr(registry, "resolve_usable", forbidden)
    outcomes = service.train(dataset, signals)
    assert outcomes[0].status in (TrainingStatus.SELECTED_BASELINE, TrainingStatus.SELECTED_LOGISTIC)


def test_public_training_exports_only_reviewed_orchestration_and_artifact_contracts():
    import safira.training as training
    assert callable(training.SafetyTrainingService)
    assert callable(training.validate_artifact)
    assert training.SafetyEstimatorArtifact
    assert training.FeaturePolicy and training.FeatureSpec and training.PreprocessingPolicy
    assert not hasattr(training, "fit_logistic_candidate")
    assert not hasattr(training, "build_feature_schema")
    assert not hasattr(training, "compare_candidates")
