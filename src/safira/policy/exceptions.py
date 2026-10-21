"""Stable errors for the private Feature 007 workflow."""

_SAFE_REASONS = frozenset({
    "input_invalid", "verification_rejected", "trusted_evidence_missing",
    "protocol_not_approved", "dataset_not_ready", "scope_incompatible",
    "reference_reproduction_failed", "origin_rejected", "inventory_mismatch",
    "patient_overlap_unknown", "patient_overlap_detected", "target_unverified",
    "insufficient_evidence", "no_feasible_cutoff", "artifact_invalid",
    "numerical_failure",
})


class PolicyError(Exception):
    """Error payloads are controlled reason codes; exception text is discarded."""

    def __init__(self, reason_code: str, *_untrusted):
        if type(reason_code) is not str or reason_code not in _SAFE_REASONS:
            reason_code = "input_invalid"
        self.reason_code = reason_code
        super().__init__(reason_code)

    def to_dict(self):
        return {"error": type(self).__name__, "reason_code": self.reason_code}

    def __repr__(self):
        return f"{type(self).__name__}(reason_code={self.reason_code!r})"


class PolicyInputError(PolicyError):
    pass


class PolicyVerificationError(PolicyError):
    pass
