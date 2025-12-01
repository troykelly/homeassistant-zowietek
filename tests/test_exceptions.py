"""Tests for Zowietek exception hierarchy."""

from __future__ import annotations

import pytest

from custom_components.zowietek.exceptions import (
    ZowietekApiError,
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekError,
    ZowietekTimeoutError,
)


class TestZowietekError:
    """Tests for the base ZowietekError exception."""

    def test_can_be_raised(self) -> None:
        """Test that ZowietekError can be raised."""
        with pytest.raises(ZowietekError):
            raise ZowietekError("Test error")

    def test_message_preserved(self) -> None:
        """Test that the error message is preserved."""
        message = "This is a test error message"
        try:
            raise ZowietekError(message)
        except ZowietekError as err:
            assert str(err) == message

    def test_inherits_from_exception(self) -> None:
        """Test that ZowietekError inherits from Exception."""
        assert issubclass(ZowietekError, Exception)

    def test_can_be_caught_as_exception(self) -> None:
        """Test that ZowietekError can be caught as Exception."""
        error = ZowietekError("Test")
        assert isinstance(error, Exception)


class TestZowietekConnectionError:
    """Tests for ZowietekConnectionError."""

    def test_can_be_raised(self) -> None:
        """Test that ZowietekConnectionError can be raised."""
        with pytest.raises(ZowietekConnectionError):
            raise ZowietekConnectionError("Connection failed")

    def test_message_preserved(self) -> None:
        """Test that the error message is preserved."""
        message = "Unable to connect to device"
        try:
            raise ZowietekConnectionError(message)
        except ZowietekConnectionError as err:
            assert str(err) == message

    def test_inherits_from_zowietek_error(self) -> None:
        """Test that ZowietekConnectionError inherits from ZowietekError."""
        assert issubclass(ZowietekConnectionError, ZowietekError)

    def test_can_be_caught_as_zowietek_error(self) -> None:
        """Test that ZowietekConnectionError can be caught as ZowietekError."""
        with pytest.raises(ZowietekError):
            raise ZowietekConnectionError("Test")


class TestZowietekAuthError:
    """Tests for ZowietekAuthError."""

    def test_can_be_raised(self) -> None:
        """Test that ZowietekAuthError can be raised."""
        with pytest.raises(ZowietekAuthError):
            raise ZowietekAuthError("Authentication failed")

    def test_message_preserved(self) -> None:
        """Test that the error message is preserved."""
        message = "Invalid credentials"
        try:
            raise ZowietekAuthError(message)
        except ZowietekAuthError as err:
            assert str(err) == message

    def test_inherits_from_zowietek_error(self) -> None:
        """Test that ZowietekAuthError inherits from ZowietekError."""
        assert issubclass(ZowietekAuthError, ZowietekError)

    def test_can_be_caught_as_zowietek_error(self) -> None:
        """Test that ZowietekAuthError can be caught as ZowietekError."""
        with pytest.raises(ZowietekError):
            raise ZowietekAuthError("Test")


class TestZowietekApiError:
    """Tests for ZowietekApiError."""

    def test_can_be_raised(self) -> None:
        """Test that ZowietekApiError can be raised."""
        with pytest.raises(ZowietekApiError):
            raise ZowietekApiError("API error")

    def test_message_preserved(self) -> None:
        """Test that the error message is preserved."""
        message = "API returned error status"
        try:
            raise ZowietekApiError(message)
        except ZowietekApiError as err:
            assert str(err) == message

    def test_inherits_from_zowietek_error(self) -> None:
        """Test that ZowietekApiError inherits from ZowietekError."""
        assert issubclass(ZowietekApiError, ZowietekError)

    def test_can_be_caught_as_zowietek_error(self) -> None:
        """Test that ZowietekApiError can be caught as ZowietekError."""
        with pytest.raises(ZowietekError):
            raise ZowietekApiError("Test")

    def test_with_status_code(self) -> None:
        """Test that ZowietekApiError can carry a status code."""
        status_code = "00003"
        error = ZowietekApiError("Invalid parameters", status_code=status_code)
        assert error.status_code == status_code
        assert "Invalid parameters" in str(error)

    def test_status_code_default_none(self) -> None:
        """Test that status_code defaults to None."""
        error = ZowietekApiError("Test error")
        assert error.status_code is None


class TestZowietekTimeoutError:
    """Tests for ZowietekTimeoutError."""

    def test_can_be_raised(self) -> None:
        """Test that ZowietekTimeoutError can be raised."""
        with pytest.raises(ZowietekTimeoutError):
            raise ZowietekTimeoutError("Request timed out")

    def test_message_preserved(self) -> None:
        """Test that the error message is preserved."""
        message = "Connection timed out after 10 seconds"
        try:
            raise ZowietekTimeoutError(message)
        except ZowietekTimeoutError as err:
            assert str(err) == message

    def test_inherits_from_connection_error(self) -> None:
        """Test that ZowietekTimeoutError inherits from ZowietekConnectionError."""
        assert issubclass(ZowietekTimeoutError, ZowietekConnectionError)

    def test_can_be_caught_as_connection_error(self) -> None:
        """Test that ZowietekTimeoutError can be caught as ZowietekConnectionError."""
        with pytest.raises(ZowietekConnectionError):
            raise ZowietekTimeoutError("Test")

    def test_can_be_caught_as_zowietek_error(self) -> None:
        """Test that ZowietekTimeoutError can be caught as ZowietekError."""
        with pytest.raises(ZowietekError):
            raise ZowietekTimeoutError("Test")


class TestExceptionHierarchy:
    """Tests for the complete exception hierarchy."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Test that all exceptions inherit from ZowietekError."""
        exceptions = [
            ZowietekConnectionError,
            ZowietekAuthError,
            ZowietekApiError,
            ZowietekTimeoutError,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, ZowietekError)

    def test_timeout_is_connection_error_subclass(self) -> None:
        """Test that TimeoutError is a subclass of ConnectionError."""
        assert issubclass(ZowietekTimeoutError, ZowietekConnectionError)

    def test_connection_errors_can_be_caught_together(self) -> None:
        """Test that connection and timeout errors can be caught together."""
        errors_caught = []

        # Test catching connection error
        try:
            raise ZowietekConnectionError("Connection failed")
        except ZowietekConnectionError as err:
            errors_caught.append(str(err))

        # Test catching timeout as connection error
        try:
            raise ZowietekTimeoutError("Timed out")
        except ZowietekConnectionError as err:
            errors_caught.append(str(err))

        assert len(errors_caught) == 2
        assert "Connection failed" in errors_caught
        assert "Timed out" in errors_caught

    def test_all_exceptions_are_distinct(self) -> None:
        """Test that each exception type can be distinguished."""
        # Create one of each
        base = ZowietekError("base")
        conn = ZowietekConnectionError("connection")
        auth = ZowietekAuthError("auth")
        api = ZowietekApiError("api")
        timeout = ZowietekTimeoutError("timeout")

        # Each should be instance of itself
        assert isinstance(base, ZowietekError)
        assert isinstance(conn, ZowietekConnectionError)
        assert isinstance(auth, ZowietekAuthError)
        assert isinstance(api, ZowietekApiError)
        assert isinstance(timeout, ZowietekTimeoutError)

        # They should not be instances of sibling classes
        assert not isinstance(conn, ZowietekAuthError)
        assert not isinstance(conn, ZowietekApiError)
        assert not isinstance(auth, ZowietekConnectionError)
        assert not isinstance(auth, ZowietekApiError)
        assert not isinstance(api, ZowietekConnectionError)
        assert not isinstance(api, ZowietekAuthError)
