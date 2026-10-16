"""Safira's immutable model definitions and exact-version registry."""

from safira.registry.definitions import (
    AdapterDeclaration,
    InputDefinition,
    LabelDefinition,
    RegisteredModelVersion,
)
from safira.registry.exceptions import (
    BindingMismatchError,
    DuplicateRegistrationError,
    IncompatibleAdapterError,
    InvalidRegistrationError,
    RegistryError,
    RegistryStorageError,
    UnattachedModelError,
    UnknownModelError,
    UnknownVersionError,
    UnsupportedTaskError,
)
from safira.registry.identity import IdentityEvidence, IdentityProvider
from safira.registry.registry import ModelRegistry, UsableRegistration

__all__ = [
    "AdapterDeclaration", "InputDefinition", "LabelDefinition", "RegisteredModelVersion",
    "ModelRegistry", "UsableRegistration", "IdentityEvidence", "IdentityProvider",
    "RegistryError", "InvalidRegistrationError", "UnsupportedTaskError",
    "IncompatibleAdapterError", "DuplicateRegistrationError", "UnknownModelError",
    "UnknownVersionError", "UnattachedModelError", "BindingMismatchError",
    "RegistryStorageError",
]
