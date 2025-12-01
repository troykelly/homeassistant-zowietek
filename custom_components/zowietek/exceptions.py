"""Exception hierarchy for the Zowietek integration."""

from __future__ import annotations


class ZowietekError(Exception):
    """Base exception for Zowietek integration.

    All Zowietek-specific exceptions inherit from this class, allowing
    consumers to catch all integration errors with a single except clause.
    """

    __slots__ = ()


class ZowietekConnectionError(ZowietekError):
    """Unable to connect to the ZowieBox device.

    Raised when a network connection cannot be established with the device,
    including DNS resolution failures, connection refused, and similar errors.
    """

    __slots__ = ()


class ZowietekAuthError(ZowietekError):
    """Authentication with the ZowieBox device failed.

    Raised when the provided credentials are rejected by the device,
    or when attempting to access an endpoint that requires authentication
    without valid credentials.
    """

    __slots__ = ()


class ZowietekApiError(ZowietekError):
    """The ZowieBox API returned an error response.

    Raised when the API returns a non-success status code, such as
    invalid parameters (00003) or other API-level errors.

    Attributes:
        status_code: The status code returned by the API, if available.
    """

    __slots__ = ("status_code",)

    def __init__(self, message: str, status_code: str | None = None) -> None:
        """Initialize ZowietekApiError.

        Args:
            message: Human-readable error description.
            status_code: Optional API status code (e.g., "00003").
        """
        super().__init__(message)
        self.status_code = status_code


class ZowietekTimeoutError(ZowietekConnectionError):
    """Request to the ZowieBox device timed out.

    Raised when a request exceeds the configured timeout duration.
    Inherits from ZowietekConnectionError as timeouts are a type of
    connection failure and can be handled similarly.
    """

    __slots__ = ()
