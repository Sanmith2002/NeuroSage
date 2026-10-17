"""Typed collection failures never interpolate synthetic sensitive values."""

from collections.abc import Mapping

import pytest

from safira.collection import CollectionAssociation, EvidenceItem, SourceProvenance
from safira.collection.validation import validate_primary_output
from safira.collection.exceptions import (
    CollectionError,
    ContributorMismatch,
    EvidenceUnavailable,
    InvalidCollectionRequest,
    InvalidPrimaryOutput,
    ProvenanceCheckFailed,
    UnknownSourceContract,
)


@pytest.mark.parametrize(
    "error_type, code",
    [
        (InvalidCollectionRequest, "invalid_collection_request"),
        (UnknownSourceContract, "unknown_source_contract"),
        (ContributorMismatch, "contributor_mismatch"),
        (ProvenanceCheckFailed, "provenance_check_failed"),
        (InvalidPrimaryOutput, "invalid_primary_output"),
        (EvidenceUnavailable, "evidence_unavailable"),
    ],
)
def test_error_categories_are_typed_and_privacy_safe(error_type, code):
    marker = "SYNTHETIC_PRIVATE_MARKER_8842"
    error = error_type(field=marker, cause=RuntimeError(marker))
    assert isinstance(error, CollectionError)
    assert error.code == code
    assert error.field == "request"
    assert marker not in str(error)
    assert marker not in repr(error)


def test_safe_field_path_is_actionable_without_echoing_values():
    error = InvalidPrimaryOutput(field="primary.value")
    assert error.field == "primary.value"
    assert "primary.value" in str(error)
    assert "invalid_primary_output" in str(error)


@pytest.mark.parametrize("bad_ref", ["", "  ", 123, None])
def test_association_validation_fails_with_safe_field_name(bad_ref):
    with pytest.raises(InvalidCollectionRequest) as caught:
        CollectionAssociation(bad_ref, "assessment", "occurrence")
    assert "association.patient_ref" in str(caught.value)
    assert str(bad_ref) not in str(caught.value) if bad_ref not in ("", None) else True


def test_nested_metadata_and_reason_cannot_reach_error_text():
    marker = "SYNTHETIC_PRIVATE_MARKER_8842"
    association = CollectionAssociation("opaque-patient", "assessment", "occurrence")
    with pytest.raises(InvalidCollectionRequest) as caught:
        SourceProvenance(
            mode="live",
            association=association,
            source_key=("model", "v1", "label"),
            assurance="verified_live_binding",
            details={"raw": object(), "observation": marker},
        )
    assert marker not in str(caught.value)
    item = EvidenceItem(
        association=association,
        source_key=("model", "v1", "label"),
        category="feature_representation",
        state="available",
        value={"observation": marker, "broken": object()},
    )
    assert item.state == "invalid"
    assert item.reason_code == "non_detachable"
    assert marker not in item.to_dict().__repr__()


def test_external_mapping_exception_is_sanitized():
    marker = "SYNTHETIC_PRIVATE_MARKER_8842"

    class BrokenMapping(Mapping):
        def __iter__(self):
            raise RuntimeError(marker)

        def __len__(self):
            return 1

        def __getitem__(self, key):
            raise KeyError(key)

    association = CollectionAssociation("opaque-patient", "assessment", "occurrence")
    with pytest.raises(InvalidCollectionRequest) as caught:
        SourceProvenance(
            mode="live", association=association, source_key=("model", "v1", "label"),
            assurance="verified_live_binding", details=BrokenMapping(),
        )
    assert marker not in str(caught.value)


def test_supplied_class_object_cannot_run_arbitrary_comparison(synthetic_metadata):
    marker = "SYNTHETIC_PRIVATE_MARKER_8842"

    class HostileClass:
        def __eq__(self, other):
            raise RuntimeError(marker)

        def __ne__(self, other):
            raise RuntimeError(marker)

    from safira.registry.definitions import LabelDefinition

    label = LabelDefinition(**synthetic_metadata["labels"][0])
    with pytest.raises(InvalidPrimaryOutput) as caught:
        validate_primary_output(0.8, label, supplied_class=HostileClass())
    assert marker not in str(caught.value)
