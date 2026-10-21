"""Private orchestration for internal synthetic research simulations."""

from safira.runtime._exceptions import RuntimeAdmissionRejected, RuntimeReadinessFailure
from safira.runtime._policy import map_runtime_policy_status
from safira.runtime._records import InternalResearchAssessmentResult, association_fingerprint
from safira.runtime._scoring import apply_frozen_runtime_score
from safira.runtime._signals import derive_runtime_signal_record
from safira.runtime._verification import admit_runtime_request


def simulate_synthetic_assessment(request, *, registry, verifier):
    """Run one exact synthetic fixture through the frozen package.

    Invalid shared trust evidence raises a safe request-level exception and
    cannot produce a status result. An admitted request with unavailable or
    invalid required runtime evidence returns a synthetic `DEFER` result.
    Unexpected programming errors intentionally propagate.
    """
    admitted = admit_runtime_request(registry, request, verifier)
    try:
        signal_record, _reference_states = derive_runtime_signal_record(admitted)
        ephemeral_score = apply_frozen_runtime_score(admitted, signal_record)
        decision = map_runtime_policy_status(admitted, ephemeral_score.value)
        status, reason = decision.status, decision.reason_code
    except RuntimeReadinessFailure as error:
        status, reason = "DEFER", error.reason_code
    result = InternalResearchAssessmentResult(
        tuple(admitted.scope_key), association_fingerprint(request.prediction), status, reason,
        request.estimator.digest, request.calibrator.digest, request.policy.digest,
    )
    # Drop references to per-query values before returning the allowlisted result.
    if "ephemeral_score" in locals():
        del ephemeral_score
    if "signal_record" in locals():
        del signal_record
    if "_reference_states" in locals():
        del _reference_states
    if "decision" in locals():
        del decision
    return result


__all__ = ()
