"""Custom exceptions for create API key use case."""


class ValidationError(ValueError):
    """Base class for validation errors."""

    pass


class ApiKeyNameAlreadyExistsError(ValueError):
    """Raised when attempting to create an API key with a name that already exists."""

    def __init__(self):
        super().__init__("API key name already exists for this tenant")


class ApiKeyCreationFailedError(ValueError):
    """Raised when API key creation fails for unexpected reasons."""

    def __init__(self, detail: str = "Failed to create API key"):
        super().__init__(detail)
