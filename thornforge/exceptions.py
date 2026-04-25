class ThornException(Exception):
    """Base class for all exceptions raised by thornforge."""

    pass

class UnreachableRepositoryURLDetected(ThornException):
    """An upload attempt was detected to a URL without a protocol prefix.

    All repository URLs must have a protocol (e.g., ``https://``).
    """

    pass

class InvalidConfiguration(ThornException):
    """Raised when configuration is invalid."""

    pass