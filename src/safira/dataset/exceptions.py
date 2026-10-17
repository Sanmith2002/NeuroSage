"""Privacy-safe errors for synthetic and research dataset construction."""


class DatasetError(ValueError):
    """Base error whose messages must not include submitted row content."""


class InvalidDatasetInput(DatasetError):
    pass


class DatasetVerificationFailed(DatasetError):
    pass


class DatasetCompatibilityError(DatasetError):
    pass


class PatientGroupingConflict(DatasetError):
    pass


class DatasetLeakageError(DatasetError):
    pass


class DatasetProtocolError(DatasetError):
    pass
