from dataclasses import replace
import pytest

from safira.policy.verification import verify_artifact_origin
from safira.policy.exceptions import PolicyVerificationError
from safira.training.artifacts import ArtifactOriginCheck


class Ledger:
    def __init__(self, check): self.check = check
    def verify_artifact(self, digest, scope, version): return self.check


def test_origin_check_must_match_exact_digest_scope_and_version():
    good = ArtifactOriginCheck("a" * 64, ("m", "v1", "l"), "v1", "ledger", "lookup", "evidence")
    verify_artifact_origin(Ledger(good), "a" * 64, ("m", "v1", "l"), "v1")
    with pytest.raises(PolicyVerificationError):
        verify_artifact_origin(Ledger(replace(good, payload_digest="b" * 64)), "a" * 64, ("m", "v1", "l"), "v1")


def test_boolean_or_status_is_not_an_origin_check():
    for value in (True, "accepted", {"accepted": True, "digest": "a" * 64}):
        with pytest.raises(PolicyVerificationError):
            verify_artifact_origin(Ledger(value), "a" * 64, ("m", "v1", "l"), "v1")
