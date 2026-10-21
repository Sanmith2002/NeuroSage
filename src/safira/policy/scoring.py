"""Private frozen Feature 005/006 scoring bridge; no per-patient API is exported."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite

from safira.policy.exceptions import PolicyVerificationError


@dataclass(frozen=True, repr=False)
class _PrivateScoreBatch:
    values: tuple[float, ...]
    row_keys: tuple[str, ...]
    def __repr__(self):
        return f"_PrivateScoreBatch(count={len(self.values)})"


def reconstruct_calibrated_scores(estimator, calibrator, signal_rows, method_parameters):
    """Apply the unchanged frozen estimator transform and frozen F006 mapping."""
    from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
    try:
        state = _reconstruct_feature_state(estimator, method_parameters)
        raw = _reconstruct_scores(state, signal_rows)
    except Exception:
        raise PolicyVerificationError("artifact_invalid") from None
    if raw.status is not None or len(raw.scores) != len(signal_rows) or raw.row_keys != tuple(
            row.row_key.value for row in signal_rows):
        raise PolicyVerificationError("artifact_invalid")
    mapping = calibrator.mapping
    if calibrator.base_family == "prevalence_baseline":
        if calibrator.method_id != "prevalence_offset_v1":
            raise PolicyVerificationError("artifact_invalid")
        values = (float(mapping["constant_probability"]),) * len(raw.scores)
    elif calibrator.base_family == "l2_logistic":
        if calibrator.method_id != "logistic_calibration_v1":
            raise PolicyVerificationError("artifact_invalid")
        values_list = []
        for score in raw.scores:
            z = float(mapping["intercept"]) + float(mapping["slope"]) * float(score)
            if not isfinite(z):
                raise PolicyVerificationError("numerical_failure")
            if z >= 0:
                value = 1.0 / (1.0 + exp(-z))
            else:
                e = exp(z)
                value = e / (1.0 + e)
            values_list.append(value)
        values = tuple(values_list)
    else:
        raise PolicyVerificationError("artifact_invalid")
    if any(not isfinite(value) or not 0 <= value <= 1 for value in values):
        raise PolicyVerificationError("numerical_failure")
    return _PrivateScoreBatch(tuple(values), tuple(raw.row_keys))

