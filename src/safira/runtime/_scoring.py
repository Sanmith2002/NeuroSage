"""Private application of frozen Feature 005/006 artifacts."""

from dataclasses import dataclass
from math import exp, isfinite

from safira.runtime._exceptions import RuntimeAdmissionRejected, RuntimeReadinessFailure


@dataclass(frozen=True, repr=False)
class _EphemeralCalibratedScore:
    value: float

    def __repr__(self):
        return "_EphemeralCalibratedScore(<private>)"


def apply_frozen_runtime_score(admitted, signal_record):
    from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
    from safira.signals.records import SignalFeatureRecord
    from safira.calibration.records import CalibrationStatus

    if type(signal_record) is not SignalFeatureRecord:
        raise RuntimeAdmissionRejected("input_invalid")
    request = admitted.request
    if (signal_record.source_key.to_tuple() != admitted.scope_key
            or request.calibrator.base_artifact_digest != request.estimator.digest
            or request.calibrator.base_family != request.estimator.family
            or request.calibrator.scope != request.estimator.scope):
        raise RuntimeAdmissionRejected("artifact_incompatible")
    method_parameters = {key: value.parameters
                         for key, value in request.original_signal_protocol.method_configs.items()}
    # The Feature 005 helpers are pure state reconstruction and application.
    # Their exceptions are allowed to propagate so programming defects are not
    # collapsed into an ordinary readiness result.
    state = _reconstruct_feature_state(request.estimator, method_parameters)
    reconstructed = _reconstruct_scores(state, (signal_record,))
    if reconstructed.status is not None:
        if reconstructed.status is CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE:
            raise RuntimeReadinessFailure("required_evidence_unavailable")
        if reconstructed.status is CalibrationStatus.NOT_READY:
            raise RuntimeReadinessFailure("evidence_not_ready")
        if reconstructed.status is CalibrationStatus.INVALID_INPUT:
            raise RuntimeReadinessFailure("evidence_invalid")
        if reconstructed.status is CalibrationStatus.INCOMPATIBLE_INPUT:
            raise RuntimeReadinessFailure("evidence_incompatible")
        raise RuntimeAdmissionRejected("artifact_invalid")
    if (len(reconstructed.scores) != 1
            or reconstructed.row_keys != (signal_record.row_key.value,)):
        raise RuntimeAdmissionRejected("artifact_invalid")
    raw = reconstructed.scores[0]
    mapping = request.calibrator.mapping
    if request.calibrator.base_family == "prevalence_baseline":
        if request.calibrator.method_id != "prevalence_offset_v1":
            raise RuntimeAdmissionRejected("artifact_invalid")
        calibrated = float(mapping["constant_probability"])
    elif request.calibrator.base_family == "l2_logistic":
        if request.calibrator.method_id != "logistic_calibration_v1":
            raise RuntimeAdmissionRejected("artifact_invalid")
        linear = float(mapping["intercept"]) + float(mapping["slope"]) * float(raw)
        if not isfinite(linear):
            raise RuntimeReadinessFailure("evidence_invalid")
        if linear >= 0:
            calibrated = 1.0 / (1.0 + exp(-linear))
        else:
            value = exp(linear)
            calibrated = value / (1.0 + value)
    else:
        raise RuntimeAdmissionRejected("artifact_invalid")
    if not isfinite(calibrated) or not 0.0 <= calibrated <= 1.0:
        raise RuntimeReadinessFailure("evidence_invalid")
    return _EphemeralCalibratedScore(calibrated)
