"""Stable private Feature 008 failures without upstream exception payloads."""


_ADMISSION_REASONS = frozenset({
    "input_invalid", "trusted_evidence_missing", "trusted_evidence_rejected",
    "prediction_rejected", "synthetic_fixture_rejected", "registry_incompatible",
    "scope_incompatible", "original_reference_incompatible", "original_inventory_incomplete",
    "original_inventory_unverified", "signal_reference_incompatible",
    "signal_protocol_unapproved", "artifact_invalid", "artifact_incompatible",
    "origin_rejected", "policy_protocol_unapproved",
})


class RuntimeAdmissionRejected(Exception):
    """Request-level invalid/untrusted input: no status result is produced."""

    def __init__(self, reason_code="trusted_evidence_rejected"):
        if reason_code not in _ADMISSION_REASONS:
            reason_code = "trusted_evidence_rejected"
        self.reason_code = reason_code
        super().__init__(reason_code)


class RuntimeReadinessFailure(Exception):
    """Admitted request whose required runtime evidence cannot support a status."""

    _REASONS = frozenset({
        "required_evidence_unavailable", "evidence_invalid", "evidence_incompatible",
        "evidence_not_ready",
    })

    def __init__(self, reason_code):
        if reason_code not in self._REASONS:
            reason_code = "evidence_not_ready"
        self.reason_code = reason_code
        super().__init__(reason_code)
