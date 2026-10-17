"""Typed collection errors with fixed, privacy-safe diagnostic fields."""

from __future__ import annotations


_SAFE_FIELDS = frozenset(
    {
        "request",
        "association.patient_ref",
        "association.assessment_ref",
        "association.occurrence_ref",
        "component.identity",
        "component.metadata",
        "component.contribution",
        "contributor",
        "model_id",
        "model_version",
        "label_id",
        "primary.value",
        "primary.value_kind",
        "primary.scale",
        "primary.class_mapping",
        "primary.meaning",
        "primary.direction",
        "primary.predicted_class",
        "primary.calibration",
        "provenance.mode",
        "provenance.assurance",
        "provenance.details",
        "provenance.source_key",
        "provenance.association",
        "evidence.category",
        "evidence.state",
        "evidence.value",
        "evidence.interpretation",
        "evidence.reason_code",
        "evidence.source_key",
        "evidence.association",
        "record.source_key",
        "record.association",
        "record.evidence",
        "record.primary",
        "record.input_verification",
        "result.records",
        "result.association",
        "input.schema",
        "input.shape",
        "input.modality",
        "input.type",
        "input.field",
        "source_contract",
    }
)


class CollectionError(Exception):
    """Base category; no caller value or external exception text enters its message."""

    code = "collection_error"

    def __init__(self, field: str | None = None, *, cause: Exception | None = None) -> None:
        self.field = field if type(field) is str and field in _SAFE_FIELDS else "request"
        # A cause may guide the caller's control flow, but its text is never retained.
        # Keeping it out of __cause__ also avoids exposing external payloads in tracebacks.
        del cause
        super().__init__(f"{self.code}: {self.field}")


class InvalidCollectionRequest(CollectionError):
    code = "invalid_collection_request"


class UnknownSourceContract(CollectionError):
    code = "unknown_source_contract"


class ContributorMismatch(CollectionError):
    code = "contributor_mismatch"


class ProvenanceCheckFailed(CollectionError):
    code = "provenance_check_failed"


class InvalidPrimaryOutput(CollectionError):
    code = "invalid_primary_output"


class EvidenceUnavailable(CollectionError):
    code = "evidence_unavailable"
