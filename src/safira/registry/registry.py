"""Registration, exact metadata lookup, and validated process-local associations."""

from dataclasses import dataclass
from pathlib import Path

from safira.adapters import AdapterCapabilities, ModelAdapter
from safira.registry.definitions import RegisteredModelVersion
from safira.registry.exceptions import (
    BindingMismatchError,
    IncompatibleAdapterError,
    InvalidRegistrationError,
    UnattachedModelError,
)
from safira.registry.identity import IdentityProvider, verify_identity
from safira.registry.storage import MetadataStore


_CAPABILITY_METHODS = {
    "prediction_probability": "predict_probability",
    "feature_representation": "extract_features",
    "repeated_outputs": "get_repeated_outputs",
    "modality_outputs": "get_modality_outputs",
    "domain_metadata": "get_domain_metadata",
    "explanation": "explain",
    "input_metadata": "get_input_metadata",
    "available_modalities": "get_available_modalities",
}


@dataclass(frozen=True)
class UsableRegistration:
    """One exact definition and the live pair validated for it.

    Owners must keep registered classifier and adapter implementations fixed.
    This association establishes compatibility, not safety-assessment readiness.
    """

    metadata: RegisteredModelVersion
    classifier: object
    adapter: ModelAdapter


def _validate_metadata(metadata: dict[str, object]) -> None:
    RegisteredModelVersion.from_dict(metadata)


def _checked_definition(definition: RegisteredModelVersion) -> RegisteredModelVersion:
    if not isinstance(definition, RegisteredModelVersion):
        raise InvalidRegistrationError("definition must be a RegisteredModelVersion.")
    # Revalidate and detach at the accepting boundary, including nested values.
    return RegisteredModelVersion.from_dict(definition.to_dict())


def _validate_adapter(
    definition: RegisteredModelVersion, adapter: ModelAdapter, *, binding: bool = False
) -> None:
    if not isinstance(adapter, ModelAdapter):
        raise IncompatibleAdapterError("adapter must implement Safira's existing ModelAdapter.")
    try:
        capabilities = adapter.capabilities
        if not isinstance(capabilities, AdapterCapabilities):
            raise TypeError
        actual = capabilities.to_dict()
        if any(type(flag) is not bool for flag in actual.values()):
            raise TypeError
    except Exception:
        raise IncompatibleAdapterError(
            "Adapter capabilities must be a valid Boolean capability snapshot."
        ) from None
    if actual != definition.adapter.capabilities.to_dict():
        error_type = BindingMismatchError if binding else IncompatibleAdapterError
        raise error_type("Adapter capabilities differ from the registered exact version.")
    required = ["predict"] + [
        method for capability, method in _CAPABILITY_METHODS.items() if actual[capability]
    ]
    for method in required:
        try:
            implementation = getattr(type(adapter), method, None)
            concrete = (
                implementation is not getattr(ModelAdapter, method)
                and callable(implementation)
                and callable(getattr(adapter, method, None))
            )
        except Exception:
            raise IncompatibleAdapterError(
                f"Adapter method {method} could not be inspected safely."
            ) from None
        if not concrete:
            raise IncompatibleAdapterError(f"Adapter must concretely implement {method}.")
    if any(label.value_source == "predict_probability" for label in definition.labels):
        if actual["prediction_probability"] is not True:
            raise IncompatibleAdapterError(
                "Probability outputs require the prediction_probability capability."
            )


def _verify_pair(definition, classifier, adapter, provider, *, binding=False) -> None:
    _validate_adapter(definition, adapter, binding=binding)
    verify_identity(
        provider, classifier, adapter,
        expected_classifier_sha256=definition.classifier_artifact["sha256"],
        expected_adapter_sha256=definition.adapter.implementation_fingerprint,
    )


class ModelRegistry:
    """Persist exact definitions while keeping validated live pairs in this handle.

    The trusted identity provider is an explicit argument to registration and
    attachment. No executable objects or providers enter the metadata catalog.
    """

    def __init__(self, storage_path: str | Path) -> None:
        self._store = MetadataStore(storage_path, validate_metadata=_validate_metadata)
        self._bindings: dict[tuple[str, str], UsableRegistration] = {}

    def register(
        self,
        definition: RegisteredModelVersion,
        classifier: object,
        adapter: ModelAdapter,
        identity_provider: IdentityProvider,
    ) -> RegisteredModelVersion:
        """Validate and commit once, then publish the submitted live association."""
        accepted = _checked_definition(definition)
        _verify_pair(accepted, classifier, adapter, identity_provider)
        self._store.insert(accepted.model_id, accepted.model_version, accepted.to_dict())
        self._bindings[(accepted.model_id, accepted.model_version)] = UsableRegistration(
            accepted, classifier, adapter
        )
        return accepted

    def get_metadata(self, model_id: str, model_version: str) -> RegisteredModelVersion:
        """Return immutable exact-version metadata independently of attachment."""
        return RegisteredModelVersion.from_dict(self._store.get(model_id, model_version))

    def attach(
        self,
        model_id: str,
        model_version: str,
        classifier: object,
        adapter: ModelAdapter,
        identity_provider: IdentityProvider,
        *,
        definition: RegisteredModelVersion,
    ) -> UsableRegistration:
        """Validate a candidate pair before publishing its active association.

        The owner supplies the candidate definition explicitly because the
        existing ModelAdapter has no static label/input/preprocessing schema API.
        Every declaration must equal the accepted record; no patient method is
        called to derive declarations. A failed attach preserves any old binding.
        """
        stored = self.get_metadata(model_id, model_version)
        candidate = _checked_definition(definition)
        if candidate != stored:
            raise BindingMismatchError("Attachment declarations differ from the registered exact version.")
        _verify_pair(stored, classifier, adapter, identity_provider, binding=True)
        usable = UsableRegistration(stored, classifier, adapter)
        self._bindings[(model_id, model_version)] = usable
        return usable

    def resolve_usable(self, model_id: str, model_version: str) -> UsableRegistration:
        """Resolve the exact association validated at registration or attachment."""
        metadata = self.get_metadata(model_id, model_version)
        usable = self._bindings.get((model_id, model_version))
        if usable is None:
            raise UnattachedModelError("Reattach the exact classifier-adapter pair before usable access.")
        if usable.metadata != metadata:
            raise BindingMismatchError("Active binding metadata differs from the stored exact version.")
        _validate_adapter(metadata, usable.adapter, binding=True)
        return usable

    def close(self) -> None:
        """Discard this handle's live bindings and close its catalog connection."""
        self._bindings.clear()
        self._store.close()

    def __enter__(self) -> "ModelRegistry":
        self._store.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
