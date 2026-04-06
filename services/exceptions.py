class NotFoundError(Exception):
    """Raised when a resource is not found."""
    pass


class AuthError(Exception):
    """Raised for authentication or authorization failures."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails. Can hold a dict of field errors."""
    pass
