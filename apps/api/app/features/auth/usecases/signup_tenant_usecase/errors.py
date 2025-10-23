"""Custom exceptions for authentication use cases."""


class ValidationError(ValueError):
    """Base class for validation errors."""

    pass


class TenantNameInvalidCharactersError(ValidationError):
    """Raised when tenant name contains invalid characters."""

    def __init__(self):
        super().__init__(
            "Tenant name can only contain alphanumeric characters, hyphens, and underscores"
        )


class PasswordTooShortError(ValidationError):
    """Raised when password is too short."""

    def __init__(self):
        super().__init__("Password must be at least 8 characters long")


class TenantAlreadyExistsError(ValueError):
    """Raised when attempting to create a tenant that already exists."""

    def __init__(self):
        super().__init__("Tenant name or email already exists")


class SignupFailedError(ValueError):
    """Raised when signup process fails for unexpected reasons."""

    def __init__(self, detail: str = "Failed to create tenant"):
        super().__init__(detail)
