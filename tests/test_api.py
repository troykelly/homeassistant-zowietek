"""Tests for ZowietekClient API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.zowietek.api import (
    STATUS_INVALID_PARAMS,
    STATUS_NOT_LOGGED_IN,
    STATUS_WRONG_PASSWORD,
    ZowietekClient,
)
from custom_components.zowietek.const import STATUS_SUCCESS
from custom_components.zowietek.exceptions import (
    ZowietekApiError,
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekTimeoutError,
)


class TestZowietekClientInit:
    """Tests for ZowietekClient initialization."""

    def test_init_with_required_params(self) -> None:
        """Test client initialization with required parameters."""
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
        )
        assert client.host == "http://192.168.1.100"
        assert client._username == "admin"
        assert client._password == "admin"

    def test_init_normalizes_host_with_scheme(self) -> None:
        """Test that host is normalized to include http scheme."""
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
        )
        assert client.host == "http://192.168.1.100"

    def test_init_preserves_existing_scheme(self) -> None:
        """Test that existing http scheme is preserved."""
        client = ZowietekClient(
            host="http://192.168.1.100",
            username="admin",
            password="admin",
        )
        assert client.host == "http://192.168.1.100"

    def test_init_preserves_https_scheme(self) -> None:
        """Test that existing https scheme is preserved."""
        client = ZowietekClient(
            host="https://192.168.1.100",
            username="admin",
            password="admin",
        )
        assert client.host == "https://192.168.1.100"

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from host."""
        client = ZowietekClient(
            host="http://192.168.1.100/",
            username="admin",
            password="admin",
        )
        assert client.host == "http://192.168.1.100"

    def test_init_with_custom_timeout(self) -> None:
        """Test client initialization with custom timeout."""
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            timeout=30,
        )
        assert client._timeout == 30

    def test_init_default_timeout(self) -> None:
        """Test that default timeout is 10 seconds."""
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
        )
        assert client._timeout == 10

    def test_init_with_session(self) -> None:
        """Test client initialization with provided session."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )
        assert client._session is mock_session
        assert client._owns_session is False

    def test_init_without_session(self) -> None:
        """Test client initialization without provided session."""
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
        )
        assert client._session is None
        assert client._owns_session is True


def _create_mock_response(
    data: dict[str, Any],
    status: int = 200,
) -> MagicMock:
    """Create a mock aiohttp response with context manager support.

    Args:
        data: JSON data to return from response.json().
        status: HTTP status code.

    Returns:
        Mock response object.
    """
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=data)
    return mock_response


def _create_mock_session(
    response: MagicMock | Exception,
) -> MagicMock:
    """Create a mock aiohttp session with context manager support.

    Args:
        response: The response to return from post() or exception to raise.

    Returns:
        Mock session object.
    """
    mock_session = MagicMock(spec=aiohttp.ClientSession)
    mock_session.closed = False
    mock_session.close = AsyncMock()

    # Create a context manager mock for the response
    if isinstance(response, Exception):
        mock_session.post = MagicMock(side_effect=response)
    else:
        # Create async context manager
        context_manager = MagicMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=context_manager)

    return mock_session


class TestZowietekClientConnection:
    """Tests for ZowietekClient connection testing."""

    @pytest.mark.asyncio
    async def test_async_test_connection_success(self) -> None:
        """Test successful connection test."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {"time": {"year": 2025, "month": 12, "day": 1}},
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_test_connection()

        assert result is True
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_test_connection_timeout(self) -> None:
        """Test connection timeout."""
        mock_session = _create_mock_session(TimeoutError())

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekTimeoutError):
            await client.async_test_connection()

    @pytest.mark.asyncio
    async def test_async_test_connection_refused(self) -> None:
        """Test connection refused."""
        mock_session = _create_mock_session(aiohttp.ClientConnectionError("Connection refused"))

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekConnectionError):
            await client.async_test_connection()


class TestZowietekClientAuthentication:
    """Tests for ZowietekClient authentication."""

    @pytest.mark.asyncio
    async def test_async_validate_credentials_success(self) -> None:
        """Test successful credential validation."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_validate_credentials()

        assert result is True

    @pytest.mark.asyncio
    async def test_async_validate_credentials_wrong_password(self) -> None:
        """Test credential validation with wrong password."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_WRONG_PASSWORD,
                "rsp": "failed",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="wrong",
            session=mock_session,
        )

        with pytest.raises(ZowietekAuthError):
            await client.async_validate_credentials()

    @pytest.mark.asyncio
    async def test_async_validate_credentials_not_logged_in(self) -> None:
        """Test credential validation when not logged in."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_NOT_LOGGED_IN,
                "rsp": "failed",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekAuthError):
            await client.async_validate_credentials()


class TestZowietekClientSystemTime:
    """Tests for ZowietekClient system time endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_system_time_success(self) -> None:
        """Test successful system time retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "time": {
                        "year": 2025,
                        "month": 12,
                        "day": 1,
                        "hour": 10,
                        "minute": 30,
                        "second": 45,
                    },
                    "time_zone_id": "GMT-10",
                },
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_system_time()

        assert result["time"]["year"] == 2025
        assert result["time"]["month"] == 12
        assert result["time"]["day"] == 1

    @pytest.mark.asyncio
    async def test_async_get_system_time_fallback_without_data_key(self) -> None:
        """Test system time retrieval when data key is missing (returns full response)."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "time": {"year": 2025},  # Data at root level, no "data" key
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_system_time()

        # Falls back to returning the full response when "data" key is missing
        assert result["status"] == STATUS_SUCCESS
        assert result["time"]["year"] == 2025


class TestZowietekClientVideoInfo:
    """Tests for ZowietekClient video info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_video_info_success(self) -> None:
        """Test successful video info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "all": {
                    "vo": [{"format": "1080p60", "switch": 1}],
                    "venc": [{"width": 1920, "height": 1080, "framerate": 60}],
                },
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_video_info()

        assert result["vo"][0]["format"] == "1080p60"
        assert result["venc"][0]["width"] == 1920

    @pytest.mark.asyncio
    async def test_async_get_input_signal_success(self) -> None:
        """Test successful input signal retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "hdmi_signal": 1,
                    "width": 1920,
                    "height": 1080,
                    "framerate": 60,
                },
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_input_signal()

        assert result["hdmi_signal"] == 1
        assert result["width"] == 1920

    @pytest.mark.asyncio
    async def test_async_get_output_info_success(self) -> None:
        """Test successful output info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "format": "1080p60",
                    "audio_switch": 1,
                    "loop_out_switch": 0,
                },
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_output_info()

        assert result["format"] == "1080p60"


class TestZowietekClientStreamInfo:
    """Tests for ZowietekClient stream info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_stream_publish_info_success(self) -> None:
        """Test successful stream publish info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "publish": [
                    {"url": "rtmp://example.com/live", "enabled": 1},
                ],
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_stream_publish_info()

        assert len(result["publish"]) == 1
        assert result["publish"][0]["url"] == "rtmp://example.com/live"

    @pytest.mark.asyncio
    async def test_async_get_stream_publish_info_empty(self) -> None:
        """Test stream publish info when no streams configured."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "publish": [],
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_stream_publish_info()

        assert result["publish"] == []

    @pytest.mark.asyncio
    async def test_async_get_stream_publish_info_missing_key(self) -> None:
        """Test stream publish info when publish key is missing."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_stream_publish_info()

        assert result["publish"] == []


class TestZowietekClientNDI:
    """Tests for ZowietekClient NDI endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_ndi_config_success(self) -> None:
        """Test successful NDI config retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "ndi_name": "ZowieBox-Test",
                    "ndi_enable": 1,
                },
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_ndi_config()

        assert result["ndi_name"] == "ZowieBox-Test"
        assert result["ndi_enable"] == 1


class TestZowietekClientWriteOperations:
    """Tests for ZowietekClient write operations."""

    @pytest.mark.asyncio
    async def test_async_set_output_format(self) -> None:
        """Test setting output format."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_output_format("1080p60")

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_loop_out_enabled(self) -> None:
        """Test enabling loop output."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_loop_out(True)

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_reboot(self) -> None:
        """Test device reboot command."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_reboot()

        mock_session.post.assert_called_once()


class TestZowietekClientErrorHandling:
    """Tests for ZowietekClient error handling."""

    @pytest.mark.asyncio
    async def test_api_error_invalid_params(self) -> None:
        """Test handling of invalid parameters error."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_INVALID_PARAMS,
                "rsp": "param group not support !!!",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekApiError) as exc_info:
            await client.async_get_system_time()

        assert exc_info.value.status_code == STATUS_INVALID_PARAMS
        assert "param group not support" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unknown_api_error_status(self) -> None:
        """Test handling of unknown API error status."""
        unknown_status = "99999"
        mock_response = _create_mock_response(
            {
                "status": unknown_status,
                "rsp": "Unknown error",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekApiError) as exc_info:
            await client.async_get_system_time()

        assert exc_info.value.status_code == unknown_status

    @pytest.mark.asyncio
    async def test_connection_error_handling(self) -> None:
        """Test handling of connection errors."""
        mock_session = _create_mock_session(aiohttp.ClientConnectionError("Connection failed"))

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekConnectionError):
            await client.async_get_system_time()

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self) -> None:
        """Test handling of timeout errors."""
        mock_session = _create_mock_session(TimeoutError())

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekTimeoutError):
            await client.async_get_system_time()

    @pytest.mark.asyncio
    async def test_invalid_json_response(self) -> None:
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock(), message="Invalid JSON")
        )

        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()

        context_manager = MagicMock()
        context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=context_manager)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekApiError):
            await client.async_get_system_time()


class TestZowietekClientRequestBehavior:
    """Tests for ZowietekClient request behavior."""

    @pytest.mark.asyncio
    async def test_login_check_flag_added_to_endpoint(self) -> None:
        """Test that login_check_flag is added to endpoint."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {},
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_get_system_time()

        call_args = mock_session.post.call_args
        url = call_args[0][0]
        assert "login_check_flag=1" in url

    @pytest.mark.asyncio
    async def test_auth_credentials_included_when_required(self) -> None:
        """Test that credentials are included for authenticated requests."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="testuser",
            password="testpass",
            session=mock_session,
        )

        await client.async_reboot()

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["user"] == "testuser"
        assert json_data["psw"] == "testpass"

    @pytest.mark.asyncio
    async def test_auth_credentials_not_included_for_read(self) -> None:
        """Test that credentials are not included for read requests."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {},
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_get_system_time()

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert "user" not in json_data
        assert "psw" not in json_data


class TestZowietekClientSessionManagement:
    """Tests for ZowietekClient session management."""

    @pytest.mark.asyncio
    async def test_session_created_when_not_provided(self) -> None:
        """Test that session is created when not provided."""
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
        )

        assert client._session is None
        assert client._owns_session is True

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            session = await client._get_session()
            assert session is mock_session
            mock_session_class.assert_called_once()

        await client.close()

    @pytest.mark.asyncio
    async def test_session_reused_when_provided(self) -> None:
        """Test that provided session is reused."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        session = await client._get_session()
        assert session is mock_session

    @pytest.mark.asyncio
    async def test_close_closes_owned_session(self) -> None:
        """Test that close() closes session when client owns it."""
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()

        object.__setattr__(client, "_session", mock_session)
        object.__setattr__(client, "_owns_session", True)

        await client.close()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_does_not_close_provided_session(self) -> None:
        """Test that close() does not close session when client doesn't own it."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.close()

        mock_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        """Test that close() can be called multiple times safely."""
        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()

        object.__setattr__(client, "_session", mock_session)
        object.__setattr__(client, "_owns_session", True)

        await client.close()
        mock_session.closed = True
        await client.close()

        mock_session.close.assert_called_once()


class TestZowietekClientContextManager:
    """Tests for ZowietekClient context manager support."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test client can be used as async context manager."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()

        async with ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        ) as client:
            assert isinstance(client, ZowietekClient)

    @pytest.mark.asyncio
    async def test_context_manager_closes_owned_session(self) -> None:
        """Test that context manager closes owned session on exit."""
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            client = ZowietekClient(
                host="192.168.1.100",
                username="admin",
                password="admin",
            )

            _ = await client._get_session()

            async with client:
                pass

            mock_session.close.assert_called_once()
