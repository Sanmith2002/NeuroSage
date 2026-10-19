"""Protected final-test boundary: ordinary Feature 004 sees references only."""

from dataclasses import fields, replace
import json

import pytest

from safira.signals.exceptions import SignalVerificationError
from safira.signals.records import (
    Feature003DatasetReference, FittedStateReference, ProtectedApplyReceipt,
    ProtectedApplyRequest,
)
from safira.signals.service import SignalExtractor


def _request():
    source = __import__("safira.signals.records", fromlist=["SignalSourceKey"]).SignalSourceKey("m", "v1", "l")
    state = FittedStateReference("state-ref", source, "knn_distance", "v1", "d", "p", "1", "manifest",
                                 "prep-v1", {"digest": "opaque-state-digest"})
    dataset = Feature003DatasetReference("d", "p", "1", "manifest", "builder-v1")
    return ProtectedApplyRequest((state,), dataset, ("knn_distance",))


class Custodian:
    def apply_frozen_state(self, request):
        return ProtectedApplyReceipt(
            status="accepted", request_fingerprint=request.fingerprint,
            dataset_reference=request.dataset_reference,
            state_ids=tuple(s.state_id for s in request.fitted_state_references),
            method_scope=request.method_scope, authority="synthetic-custodian",
            evidence_ref="synthetic-receipt-evidence",
        )


def _extractor(handoff):
    extractor = object.__new__(SignalExtractor)
    extractor.protected_apply = handoff
    return extractor


def test_protected_request_contains_only_frozen_state_and_exact_scope_references():
    request = _request()
    rendered = json.dumps(request.to_dict(), sort_keys=True)
    assert "protected_rows" not in rendered and "outcome" not in rendered
    assert "correctness" not in rendered and "transformed_values" not in rendered
    assert "patient_group_ref" not in rendered and "patient_ref" not in rendered
    assert "opaque-state-digest" in rendered
    assert {field.name for field in fields(request)} == {
        "fitted_state_references", "dataset_reference", "method_scope", "fingerprint"
    }


def test_protected_handoff_accepts_only_receipt_bound_to_exact_request():
    request = _request()
    receipt = _extractor(Custodian()).apply_protected(request)
    assert receipt.status == "accepted"
    assert receipt.request_fingerprint == request.fingerprint
    assert "protected" not in json.dumps(receipt.to_dict()).lower()

    class Mismatched:
        def apply_frozen_state(self, submitted):
            return replace(Custodian().apply_frozen_state(submitted), request_fingerprint="other-request")

    with pytest.raises(SignalVerificationError):
        _extractor(Mismatched()).apply_protected(request)

    class WrongScope:
        def apply_frozen_state(self, submitted):
            receipt = Custodian().apply_frozen_state(submitted)
            return replace(receipt, method_scope=("domain_familiarity",))

    with pytest.raises(SignalVerificationError):
        _extractor(WrongScope()).apply_protected(request)


def test_accepted_status_without_exact_scope_evidence_is_rejected():
    request = _request()

    class AssertionOnly:
        def apply_frozen_state(self, submitted):
            return ProtectedApplyReceipt(status="accepted", request_fingerprint=submitted.fingerprint,
                                         dataset_reference=submitted.dataset_reference,
                                         state_ids=(), method_scope=(), authority="",
                                         evidence_ref="")

    with pytest.raises(SignalVerificationError):
        _extractor(AssertionOnly()).apply_protected(request)


def test_custodian_receipt_requires_an_independently_recorded_exact_request():
    request = _request()

    class LedgerCustodian:
        def __init__(self, accepted_requests=()):
            # This ledger represents custodian-controlled evidence external to the request.
            self.accepted_requests = set(accepted_requests)

        def apply_frozen_state(self, submitted):
            accepted = submitted.fingerprint in self.accepted_requests
            return ProtectedApplyReceipt(
                status="accepted" if accepted else "rejected",
                request_fingerprint=submitted.fingerprint,
                dataset_reference=submitted.dataset_reference,
                state_ids=tuple(state.state_id for state in submitted.fitted_state_references),
                method_scope=submitted.method_scope,
                authority="synthetic-custodian-ledger",
                evidence_ref="external-entry" if accepted else "no-independent-entry",
            )

    # Correctly echoed request fields do not suffice when the custodian ledger
    # contains no executed apply record for that exact request.
    with pytest.raises(SignalVerificationError):
        _extractor(LedgerCustodian()).apply_protected(request)

    accepted = _extractor(LedgerCustodian((request.fingerprint,))).apply_protected(request)
    assert accepted.status == "accepted"
