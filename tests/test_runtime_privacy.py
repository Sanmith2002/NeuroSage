import json

import pytest

from runtime_fixtures import build_runtime_fixture
from safira.runtime._exceptions import RuntimeAdmissionRejected
from safira.runtime._service import simulate_synthetic_assessment


def test_result_repr_str_and_serialization_exclude_identifiers_scores_and_evidence(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    result = simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                           verifier=fixture.verifier)
    surfaces = (repr(result), str(result), json.dumps(result.to_dict(), sort_keys=True))
    for surface in surfaces:
        for private_value in ("synthetic-query-patient", "synthetic-query-assessment",
                              "synthetic-query-occurrence", "0.73", "score", "evidence"):
            assert private_value not in surface


def test_safe_failure_and_exception_chaining_do_not_copy_verifier_payload(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    fixture.verifier.allow_synthetic = False
    with pytest.raises(RuntimeAdmissionRejected) as caught:
        simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                      verifier=fixture.verifier)
    assert str(caught.value) == "synthetic_fixture_rejected"
    assert caught.value.__cause__ is None
    assert "patient" not in repr(caught.value).lower()


def test_runtime_path_emits_no_diagnostics_or_logs(registered_collection, caplog):
    fixture = build_runtime_fixture(registered_collection)
    simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                  verifier=fixture.verifier)
    assert not caplog.records
