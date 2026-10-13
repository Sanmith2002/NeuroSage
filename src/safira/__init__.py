"""Safira clinical AI reliability and safety framework."""

from safira.adapters import (
    AdapterCapabilities,
    CapabilityNotSupportedError,
    ModelAdapter,
)
from safira.context import SafetyContext
from safira.models import SafetyAssessment, SafetyStatus

__version__ = "0.1.0"

__all__ = [
    "AdapterCapabilities",
    "CapabilityNotSupportedError",
    "ModelAdapter",
    "SafetyAssessment",
    "SafetyContext",
    "SafetyStatus",
]