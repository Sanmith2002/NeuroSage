"""Identity evidence checked at the boundary to an owner-supplied trusted loader.

A digest cannot prove the origin of an arbitrary Python object. The configured
provider must observe/control loading and attest the relationship to the actual
supplied pair. Safira checks the evidence and compares both expected digests;
it does not serialize models, run predictions, or authenticate arbitrary code.
"""

from dataclasses import dataclass
import re
from typing import Protocol

from safira.adapters import ModelAdapter
from safira.registry.exceptions import BindingMismatchError, IncompatibleAdapterError


def _check_sha256(value: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise IncompatibleAdapterError(
            "Identity fingerprints must contain 64 lowercase SHA-256 hex characters."
        )


@dataclass(frozen=True)
class IdentityEvidence:
    """Immutable digests and the trusted loader's live-pair attestation."""

    classifier_sha256: str
    adapter_sha256: str
    loaded_pair_verified: bool

    def __post_init__(self) -> None:
        _check_sha256(self.classifier_sha256)
        _check_sha256(self.adapter_sha256)
        if type(self.loaded_pair_verified) is not bool:
            raise IncompatibleAdapterError("Identity attestation must be an actual Boolean.")


class IdentityProvider(Protocol):
    """Integration contract implemented by the classifier owner/trusted loader.

    Hash exact immutable artifact bytes with SHA-256. Multi-file artifacts use
    a deterministic manifest of normalized relative paths and content digests;
    an in-memory model may use owner-defined deterministic non-patient state.
    Attest only the pair actually associated with those artifacts. Return false
    or raise when that association cannot be verified. Never use patient data
    or invoke prediction. Providers and artifact bytes are not persisted.
    """

    def identify_loaded_pair(
        self, classifier: object, adapter: ModelAdapter
    ) -> IdentityEvidence:
        """Compute identity evidence for these exact live objects."""
        ...


def verify_identity(
    provider: IdentityProvider | None,
    classifier: object,
    adapter: ModelAdapter,
    *,
    expected_classifier_sha256: str,
    expected_adapter_sha256: str,
) -> IdentityEvidence:
    """Obtain fresh evidence and require agreement with declared/stored identity.

    The provider is explicitly supplied by the trusted owning integration for
    each check. No fallback to class names, object IDs, or caller digest strings
    establishes a usable identity. Provider failures are sanitized.
    """
    _check_sha256(expected_classifier_sha256)
    _check_sha256(expected_adapter_sha256)
    try:
        identify = getattr(provider, "identify_loaded_pair", None)
        if not callable(identify):
            raise IncompatibleAdapterError("A trusted identity provider is required.")
        evidence = identify(classifier, adapter)
        if not isinstance(evidence, IdentityEvidence):
            raise IncompatibleAdapterError("The provider must return IdentityEvidence.")
        # Recheck even an already constructed value at this integration boundary.
        checked = IdentityEvidence(
            evidence.classifier_sha256,
            evidence.adapter_sha256,
            evidence.loaded_pair_verified,
        )
    except Exception:
        raise IncompatibleAdapterError(
            "Identity evidence could not be verified; supply a trusted loader/provider."
        ) from None
    if checked.loaded_pair_verified is not True:
        raise IncompatibleAdapterError(
            "The trusted provider could not verify the loaded classifier-adapter pair."
        )
    if (
        checked.classifier_sha256 != expected_classifier_sha256
        or checked.adapter_sha256 != expected_adapter_sha256
    ):
        raise BindingMismatchError(
            "Classifier or adapter fingerprint differs from the expected exact version."
        )
    return checked
