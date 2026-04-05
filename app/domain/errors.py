class AppError(Exception):
    """Base application error."""


class InvalidAnalyticsRequest(AppError):
    """Raised when analytics input is invalid."""
