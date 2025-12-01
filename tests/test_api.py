"""Tests for ZowietekClient API client."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.zowietek.api import ZowietekClient
from custom_components.zowietek.const import (
    STATUS_INVALID_PARAMS,
    STATUS_NOT_LOGGED_IN,
    STATUS_SUCCESS,
)
from custom_components.zowietek.exceptions import (
    ZowietekApiError,
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekTimeoutError,
)

if TYPE_CHECKING:
    from custom_components.zowietek.models import (
        ZowietekAudioInfo,
        ZowietekNetworkInfo,
        ZowietekStreamInfo,
        ZowietekSystemInfo,
        ZowietekVideoInfo,
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
    data: dict[str, str | int | bool],
    status: int = 200,
) -> MagicMock:
    """Create a mock aiohttp response.

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
    """Create a mock aiohttp session.

    Args:
        response: The response to return from post() or exception to raise.

    Returns:
        Mock session object.
    """
    mock_session = MagicMock(spec=aiohttp.ClientSession)
    mock_session.closed = False
    mock_session.close = AsyncMock()

    if isinstance(response, Exception):
        mock_session.post = AsyncMock(side_effect=response)
    else:
        mock_session.post = AsyncMock(return_value=response)

    return mock_session


class TestZowietekClientAuthentication:
    """Tests for ZowietekClient authentication."""

    @pytest.mark.asyncio
    async def test_async_login_success(self) -> None:
        """Test successful authentication."""
        mock_response = _create_mock_response({"status": STATUS_SUCCESS, "rsp": "succeed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_login()

        assert result is True
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_login_failure_wrong_credentials(self) -> None:
        """Test authentication failure with wrong credentials."""
        mock_response = _create_mock_response({"status": STATUS_NOT_LOGGED_IN, "rsp": "failed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="wrong",
            session=mock_session,
        )

        with pytest.raises(ZowietekAuthError):
            await client.async_login()

    @pytest.mark.asyncio
    async def test_async_login_connection_refused(self) -> None:
        """Test authentication when connection is refused."""
        mock_session = _create_mock_session(aiohttp.ClientConnectionError("Connection refused"))

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekConnectionError):
            await client.async_login()

    @pytest.mark.asyncio
    async def test_async_login_timeout(self) -> None:
        """Test authentication timeout."""
        mock_session = _create_mock_session(TimeoutError())

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekTimeoutError):
            await client.async_login()


class TestZowietekClientSystemInfo:
    """Tests for ZowietekClient system info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_system_info_success(self) -> None:
        """Test successful system info retrieval."""
        expected_response: ZowietekSystemInfo = {
            "status": STATUS_SUCCESS,
            "rsp": "succeed",
            "device_name": "ZowieBox-Test",
            "device_serial": "ABC123",
            "firmware_version": "1.0.0",
            "hardware_version": "2.0",
            "mac_address": "00:11:22:33:44:55",
            "model": "ZowieBox 4K",
        }
        mock_response = _create_mock_response(expected_response)
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_system_info()

        assert result["status"] == STATUS_SUCCESS
        assert result["device_name"] == "ZowieBox-Test"
        assert result["firmware_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_async_get_system_info_auth_required(self) -> None:
        """Test system info when not authenticated."""
        mock_response = _create_mock_response({"status": STATUS_NOT_LOGGED_IN, "rsp": "failed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekAuthError):
            await client.async_get_system_info()


class TestZowietekClientVideoInfo:
    """Tests for ZowietekClient video info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_video_info_success(self) -> None:
        """Test successful video info retrieval."""
        expected_response: ZowietekVideoInfo = {
            "status": STATUS_SUCCESS,
            "rsp": "succeed",
            "input_signal": True,
            "input_width": 1920,
            "input_height": 1080,
            "input_framerate": 60,
            "output_format": "1080p60",
            "loop_out_enabled": True,
        }
        mock_response = _create_mock_response(expected_response)
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_video_info()

        assert result["status"] == STATUS_SUCCESS
        assert result["input_width"] == 1920
        assert result["input_height"] == 1080


class TestZowietekClientAudioInfo:
    """Tests for ZowietekClient audio info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_audio_info_success(self) -> None:
        """Test successful audio info retrieval."""
        expected_response: ZowietekAudioInfo = {
            "status": STATUS_SUCCESS,
            "rsp": "succeed",
            "audio_enabled": True,
            "input_type": "hdmi",
            "codec": "aac",
            "sample_rate": 48000,
            "bitrate": 128,
            "volume": 80,
        }
        mock_response = _create_mock_response(expected_response)
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_audio_info()

        assert result["status"] == STATUS_SUCCESS
        assert result["volume"] == 80
        assert result["codec"] == "aac"


class TestZowietekClientStreamInfo:
    """Tests for ZowietekClient stream info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_stream_info_success(self) -> None:
        """Test successful stream info retrieval."""
        expected_response: ZowietekStreamInfo = {
            "status": STATUS_SUCCESS,
            "rsp": "succeed",
            "ndi_enabled": True,
            "ndi_name": "ZowieBox-Test",
            "rtmp_enabled": False,
            "rtmp_url": "",
            "srt_enabled": False,
            "srt_url": "",
        }
        mock_response = _create_mock_response(expected_response)
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_stream_info()

        assert result["status"] == STATUS_SUCCESS
        assert result["ndi_enabled"] is True
        assert result["ndi_name"] == "ZowieBox-Test"


class TestZowietekClientNetworkInfo:
    """Tests for ZowietekClient network info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_network_info_success(self) -> None:
        """Test successful network info retrieval."""
        expected_response: ZowietekNetworkInfo = {
            "status": STATUS_SUCCESS,
            "rsp": "succeed",
            "ip_address": "192.168.1.100",
            "netmask": "255.255.255.0",
            "gateway": "192.168.1.1",
            "dhcp_enabled": False,
            "mac_address": "00:11:22:33:44:55",
        }
        mock_response = _create_mock_response(expected_response)
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_network_info()

        assert result["status"] == STATUS_SUCCESS
        assert result["ip_address"] == "192.168.1.100"
        assert result["dhcp_enabled"] is False


class TestZowietekClientWriteOperations:
    """Tests for ZowietekClient write operations."""

    @pytest.mark.asyncio
    async def test_async_set_ndi_enabled_true(self) -> None:
        """Test enabling NDI stream."""
        mock_response = _create_mock_response({"status": STATUS_SUCCESS, "rsp": "succeed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_ndi_enabled(True)

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        url = call_args[0][0]
        assert "stream" in url.lower()

    @pytest.mark.asyncio
    async def test_async_set_ndi_enabled_false(self) -> None:
        """Test disabling NDI stream."""
        mock_response = _create_mock_response({"status": STATUS_SUCCESS, "rsp": "succeed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_ndi_enabled(False)

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_rtmp_enabled(self) -> None:
        """Test setting RTMP enabled status."""
        mock_response = _create_mock_response({"status": STATUS_SUCCESS, "rsp": "succeed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_rtmp_enabled(True)

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_srt_enabled(self) -> None:
        """Test setting SRT enabled status."""
        mock_response = _create_mock_response({"status": STATUS_SUCCESS, "rsp": "succeed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_srt_enabled(True)

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_reboot(self) -> None:
        """Test device reboot command."""
        mock_response = _create_mock_response({"status": STATUS_SUCCESS, "rsp": "succeed"})
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
        mock_response = _create_mock_response({"status": STATUS_INVALID_PARAMS, "rsp": "failed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekApiError) as exc_info:
            await client.async_get_system_info()

        assert exc_info.value.status_code == STATUS_INVALID_PARAMS

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
            await client.async_get_system_info()

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
            await client.async_get_system_info()

    @pytest.mark.asyncio
    async def test_invalid_json_response(self) -> None:
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock(), message="Invalid JSON")
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekApiError):
            await client.async_get_system_info()

    @pytest.mark.asyncio
    async def test_unknown_api_error_status(self) -> None:
        """Test handling of unknown API error status."""
        unknown_status = "99999"
        mock_response = _create_mock_response({"status": unknown_status, "rsp": "failed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        with pytest.raises(ZowietekApiError) as exc_info:
            await client.async_get_system_info()

        assert exc_info.value.status_code == unknown_status


class TestZowietekClientRequestWithNoneData:
    """Tests for request with None data parameter."""

    @pytest.mark.asyncio
    async def test_request_with_none_data(self) -> None:
        """Test that request works when data parameter is None."""
        mock_response = _create_mock_response({"status": STATUS_SUCCESS, "rsp": "succeed"})
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        # Manually call _request with None data
        await client._request("/test?option=getinfo", None)

        # Verify the request was made
        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args[1]

        # The data should have only credentials
        assert call_kwargs["json"]["user"] == "admin"
        assert call_kwargs["json"]["psw"] == "admin"


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

        # Access session to trigger creation
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

        # Manually set session for testing
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

        # Manually set session for testing
        object.__setattr__(client, "_session", mock_session)
        object.__setattr__(client, "_owns_session", True)

        await client.close()
        # Second call should not raise
        mock_session.closed = True
        await client.close()

        # Should only be called once
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

            # Trigger session creation
            _ = await client._get_session()

            async with client:
                pass

            mock_session.close.assert_called_once()
