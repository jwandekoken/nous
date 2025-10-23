"""Custom exceptions for delete API key use case."""


class InvalidApiKeyIdFormatError(ValueError):
    """Raised when the API key ID format is invalid."""

    def __init__(self):
        super().__init__("Invalid API key ID format")


class ApiKeyNotFoundError(ValueError):
    """Raised when the API key to delete is not found."""

    def __init__(self):
        super().__init__("API key not found")


class ApiKeyAccessDeniedError(ValueError):
    """Raised when attempting to delete an API key that doesn't belong to the tenant."""

    def __init__(self):
        super().__init__("Access denied")
