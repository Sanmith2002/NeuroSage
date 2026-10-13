class CapabilityNotSupportedError(RuntimeError):
    """
    Raised when Safira requests optional evidence that an adapter
    does not support.
    """