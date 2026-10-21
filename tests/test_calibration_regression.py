"""Lifecycle regression guards for Features 001–005 public behavior."""

import copy


def test_calibration_does_not_retrain_primary_or_upstream_estimators(monkeypatch, registered_collection):
    from safira.calibration.records import CalibrationStatus
    from test_calibration_acceptance import _service_case

    registry, dataset, signals, artifacts, service, _, _ = _service_case(registered_collection)
    snapshots = {key: artifact.to_dict() for key, artifact in artifacts.items()}
    import safira.training.service as training_service
    import safira.training.features as training_features
    import safira.signals.service as signal_service

    monkeypatch.setattr(training_service.SafetyTrainingService, "train",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Feature 005 retraining called")))
    monkeypatch.setattr(training_features, "fit_preprocessing",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("preprocessing refit called")))
    monkeypatch.setattr(training_features, "build_feature_schema",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("schema refit called")))
    monkeypatch.setattr(signal_service.SignalExtractor, "extract_record",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Feature 004 extraction called")))

    outcomes = service.calibrate(dataset, signals, artifacts)
    assert outcomes[0].status is CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED
    assert {key: artifact.to_dict() for key, artifact in artifacts.items()} == snapshots
    # Established upstream types remain importable from their original modules.
    from safira import AdapterCapabilities, ModelAdapter, SafetyAssessment
    from safira.collection import PredictionRecord
    from safira.dataset import DatasetBuildResult
    from safira.signals import SignalFeatureSet
    from safira.training.records import SafetyEstimatorArtifact
    assert all(item is not None for item in
               (AdapterCapabilities, ModelAdapter, SafetyAssessment, PredictionRecord,
                DatasetBuildResult, SignalFeatureSet, SafetyEstimatorArtifact))
