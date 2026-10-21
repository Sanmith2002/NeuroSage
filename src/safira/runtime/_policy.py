"""Private application of the exact frozen Feature 007 policy cutoff."""

from dataclasses import dataclass
from math import isfinite

from safira.runtime._exceptions import RuntimeAdmissionRejected


@dataclass(frozen=True, repr=False)
class _PolicyDecision:
    status: str
    reason_code: str

    def __repr__(self):
        return f"_PolicyDecision(status={self.status!r}, reason_code={self.reason_code!r})"


def map_runtime_policy_status(admitted, calibrated_score):
    """Compare one ephemeral finite score using only Feature 007's frozen rule."""
    request = admitted.request
    policy = request.policy
    if (type(calibrated_score) not in (int, float) or type(calibrated_score) is bool
            or not isfinite(calibrated_score) or not 0.0 <= calibrated_score <= 1.0):
        raise ValueError("runtime_score_invalid")
    comparison = policy.selection_configuration["comparison"]
    cutoff = policy.selection.cutoff
    if comparison == ">=":
        accepted = calibrated_score >= cutoff
    elif comparison == ">":
        accepted = calibrated_score > cutoff
    else:
        raise RuntimeAdmissionRejected("artifact_invalid")
    return _PolicyDecision("TRUST", "cutoff_satisfied") if accepted else _PolicyDecision(
        "CAUTION", "cutoff_not_satisfied")
