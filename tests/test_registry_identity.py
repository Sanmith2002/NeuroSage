"""T003/T006: artifact evidence and the trusted-loader boundary."""

from dataclasses import FrozenInstanceError, replace
from hashlib import sha256

import pytest

from safira.registry.exceptions import BindingMismatchError, IncompatibleAdapterError
from safira.registry.identity import IdentityEvidence, verify_identity


def verify(pair, **changes):
    classifier, adapter, provider = pair
    arguments = {
        "provider": provider,
        "classifier": classifier,
        "adapter": adapter,
        "expected_classifier_sha256": sha256(provider.classifier_artifact).hexdigest(),
        "expected_adapter_sha256": sha256(provider.adapter_artifact).hexdigest(),
    }
    arguments.update(changes)
    return verify_identity(**arguments)


def test_deterministic_evidence_for_exact_live_pair(loaded_pair):
    first = verify(loaded_pair)
    assert first == verify(loaded_pair)
    classifier, adapter, provider = loaded_pair
    assert first.classifier_sha256 == sha256(classifier.artifact).hexdigest()
    assert first.adapter_sha256 == sha256(adapter.implementation_artifact).hexdigest()
    assert first.loaded_pair_verified is True
    assert provider.calls == [(classifier, adapter), (classifier, adapter)]
    with pytest.raises(FrozenInstanceError):
        first.classifier_sha256 = "0" * 64


def test_same_bytes_do_not_attest_an_unobserved_object(loaded_pair):
    classifier, _, _ = loaded_pair
    unobserved = type(classifier)(classifier.artifact)
    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair, classifier=unobserved)


def test_different_adapter_or_classifier_link_is_rejected(loaded_pair):
    classifier, adapter, _ = loaded_pair
    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair, adapter=type(adapter)(classifier))
    adapter.classifier = object()
    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair)


@pytest.mark.parametrize("field", ["expected_classifier_sha256", "expected_adapter_sha256"])
def test_fingerprint_mismatch_is_rejected(loaded_pair, field):
    with pytest.raises(BindingMismatchError):
        verify(loaded_pair, **{field: "0" * 64})


@pytest.mark.parametrize("field", ["expected_classifier_sha256", "expected_adapter_sha256"])
def test_uncheckable_expected_identity_is_rejected_before_provider_call(loaded_pair, field):
    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair, **{field: "unverified-identity"})
    assert loaded_pair[2].calls == []


def test_changed_adapter_material_cannot_keep_its_attestation(loaded_pair):
    loaded_pair[1].implementation_artifact = b"changed synthetic implementation"
    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair)


@pytest.mark.parametrize("provider", [None, object()])
def test_missing_provider_fails_closed(loaded_pair, provider):
    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair, provider=provider)


def test_provider_failure_does_not_expose_exception_payload(loaded_pair):
    class FailingProvider:
        def identify_loaded_pair(self, classifier, adapter):
            raise ValueError("synthetic-restricted-marker")

    with pytest.raises(IncompatibleAdapterError) as error:
        verify(loaded_pair, provider=FailingProvider())
    assert "synthetic-restricted-marker" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("result", [None, {}, "identity-assertion"])
def test_unstructured_assertions_are_not_identity_evidence(loaded_pair, result):
    class AssertionProvider:
        def identify_loaded_pair(self, classifier, adapter):
            return result

    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair, provider=AssertionProvider())


@pytest.mark.parametrize("value", [None, "", "name-only", "a" * 63, "g" * 64, 123])
def test_malformed_digest_is_rejected(value):
    with pytest.raises(IncompatibleAdapterError):
        IdentityEvidence(value, "b" * 64, True)
    with pytest.raises(IncompatibleAdapterError):
        IdentityEvidence("a" * 64, value, True)


@pytest.mark.parametrize("attestation", [None, 1, 0, "true"])
def test_attestation_requires_actual_boolean(attestation):
    with pytest.raises(IncompatibleAdapterError):
        IdentityEvidence("a" * 64, "b" * 64, attestation)


def test_false_attestation_fails_verification(loaded_pair):
    evidence = replace(verify(loaded_pair), loaded_pair_verified=False)

    class UnableToVerifyProvider:
        def identify_loaded_pair(self, classifier, adapter):
            return evidence

    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair, provider=UnableToVerifyProvider())


def test_evidence_is_revalidated_at_boundary(loaded_pair):
    evidence = verify(loaded_pair)
    object.__setattr__(evidence, "loaded_pair_verified", 1)

    class MalformedProvider:
        def identify_loaded_pair(self, classifier, adapter):
            return evidence

    with pytest.raises(IncompatibleAdapterError):
        verify(loaded_pair, provider=MalformedProvider())
