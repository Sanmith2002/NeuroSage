from dataclasses import replace

import pytest

from safira.calibration.verification import verify_prediction_admission
from safira.collection import SourceProvenance
from safira.signals.exceptions import SignalInputError
from signals_fixtures import SyntheticSignalVerifier, make_live_record, signal_protocol


@pytest.mark.parametrize("field,value", [("model_version", "v9"), ("label_id", "unknown")])
def test_unknown_exact_model_version_or_label_is_rejected(registered_collection, field, value):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    changed_key = (record.model_id, value if field == "model_version" else record.model_version,
                   value if field == "label_id" else record.label_id)
    changed = replace(record, **{field: value},
                      provenance=replace(record.provenance, source_key=changed_key),
                      evidence=tuple(replace(item, source_key=changed_key) for item in record.evidence))
    verifier = SyntheticSignalVerifier()
    verifier.admit(changed)
    protocol = signal_protocol(record.source_key, {"evidence_coverage": {"required_evidence": []}})
    with pytest.raises(Exception):
        verify_prediction_admission(registry, protocol, verifier, changed)


def test_registered_prediction_semantics_and_adapter_identity_are_rechecked(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    bad = replace(record, primary=replace(record.primary, predicted_class="negative"))
    verifier = SyntheticSignalVerifier()
    verifier.admit(bad)
    protocol = signal_protocol(record.source_key, {"evidence_coverage": {"required_evidence": []}})
    with pytest.raises(Exception):
        verify_prediction_admission(registry, protocol, verifier, bad)

    bad_source = (record.model_id, record.model_version, "label-a")
    forged = replace(record, provenance=SourceProvenance(
        "live", record.association, bad_source, record.provenance.assurance,
        {**record.provenance.details, "adapter_id": "other-adapter"},
    ))
    verifier2 = SyntheticSignalVerifier()
    verifier2.admit(forged)
    with pytest.raises(Exception):
        verify_prediction_admission(registry, protocol, verifier2, forged)
