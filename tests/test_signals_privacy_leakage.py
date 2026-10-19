import json

import pytest

from safira.signals.exceptions import SignalVerificationError

from test_signals_acceptance import _dataset_authority
from signals_fixtures import SyntheticSignalVerifier, make_live_record, make_synthetic_feature003_result, signal_protocol


def test_failed_dataset_verification_has_fixed_safe_error_and_no_payload_echo(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register, model_id="privacy", labels=("label-a",))
    verifier = SyntheticSignalVerifier()
    # This record is deliberately not independently admitted.
    dataset = make_synthetic_feature003_result({"train": ((record, "person-private-77"),)})
    from safira.signals.records import Feature003DatasetReference, SignalMethodConfig, SignalProtocol, SignalSourceKey
    ref = Feature003DatasetReference("d", "p", "1", dataset.manifest_reference, "builder-v1")
    protocol = SignalProtocol("p", "1", (SignalSourceKey(*record.source_key),),
        {"bernoulli_entropy": SignalMethodConfig("bernoulli_entropy", "v1", {"log_base": 2})}, {})
    extractor = __import__("safira.signals.service", fromlist=["SignalExtractor"]).SignalExtractor(
        registry, protocol, verifier, dataset_verifier=_dataset_authority(verifier, ref))
    with pytest.raises(SignalVerificationError) as caught:
        extractor.build_feature_set(dataset, ref)
    assert str(caught.value) == "prediction_scope_unverified"
    assert "person-private-77" not in str(caught.value)
    assert record.primary.value.__class__ is float
