"""Public API allowlist for Feature 006; no per-patient or policy operations."""


def test_calibration_exports_only_protocol_service_safe_records_and_artifact_tools():
    import safira.calibration as calibration

    allowed = {
        "CalibrationProtocol", "CalibrationStatus", "CalibrationOutcome", "CalibratorArtifact",
        "CalibrationInputVerifier", "CalibrationService", "export_calibrator_artifact",
        "validate_calibrator_artifact", "CalibrationError", "CalibrationInputError",
        "CalibrationVerificationError", "CalibrationCompatibilityError",
    }
    assert set(calibration.__all__) == allowed
    assert all(hasattr(calibration, name) for name in allowed)
    assert not any(hasattr(calibration, name) for name in
                   ("predict", "predict_proba", "apply", "calibrate", "SafetyAssessment"))
    assert not any(hasattr(calibration.CalibrationService, name) for name in
                   ("predict", "predict_proba", "apply", "score_patient"))
    assert not any(hasattr(calibration.CalibratorArtifact, name) for name in
                   ("predict", "predict_proba", "apply"))
