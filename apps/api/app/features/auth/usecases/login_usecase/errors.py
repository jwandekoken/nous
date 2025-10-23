"""Custom exceptions for login use case."""


class InvalidCredentialsError(ValueError):
    """Raised when email or password is incorrect."""

    def __init__(self):
        super().__init__("Incorrect email or password")


class AccountLockedError(ValueError):
    """Raised when account is temporarily locked due to failed login attempts."""

    def __init__(self):
        super().__init__("Account is temporarily locked due to failed login attempts")


class AccountDisabledError(ValueError):
    """Raised when account is disabled."""

    def __init__(self):
        super().__init__("Account is disabled")
