"""Typed registry failures. Messages must never include raw submitted payloads."""


class RegistryError(RuntimeError):
    """Base class for failures at Safira's registry boundary."""


class InvalidRegistrationError(RegistryError):
    """A required declaration is missing, malformed, or outside its schema."""


class UnsupportedTaskError(InvalidRegistrationError):
    """The declared task is outside supervised multi-label classification."""


class IncompatibleAdapterError(RegistryError):
    """The adapter or its identity evidence cannot establish compatibility."""


class DuplicateRegistrationError(RegistryError):
    """The immutable model identifier/version key is already registered."""


class UnknownModelError(RegistryError):
    """No registered version exists for the requested model identifier."""


class UnknownVersionError(RegistryError):
    """The model exists, but its requested exact version does not."""


class UnattachedModelError(RegistryError):
    """Metadata exists without a validated live classifier-adapter binding."""


class BindingMismatchError(RegistryError):
    """A candidate pair differs from the immutable registration identity."""


class RegistryStorageError(RegistryError):
    """The catalog cannot be safely opened, read, or committed."""
