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


class TestZowietekClientDeviceInfo:
    """Tests for ZowietekClient device info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_device_info_success(self) -> None:
        """Test successful device info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "devicesn": "ZBOX-ABC123",
                    "devicename": "ZowieBox-Office",
                    "softver": "1.2.3",
                    "hardver": "2.0",
                    "mac": "00:11:22:33:44:55",
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

        result = await client.async_get_device_info()

        assert result["devicesn"] == "ZBOX-ABC123"
        assert result["devicename"] == "ZowieBox-Office"
        assert result["softver"] == "1.2.3"

    @pytest.mark.asyncio
    async def test_async_get_device_info_fallback_without_data_key(self) -> None:
        """Test device info retrieval when data key is missing (returns full response)."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "devicesn": "ZBOX-ABC123",  # Data at root level, no "data" key
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_device_info()

        # Falls back to returning the full response when "data" key is missing
        assert result["status"] == STATUS_SUCCESS
        assert result["devicesn"] == "ZBOX-ABC123"


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
                    "machinename": "ZowieBox-Test",
                    "switch": 1,
                    "mode_id": 1,
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

        assert result["machinename"] == "ZowieBox-Test"
        assert result["switch"] == 1


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

    @pytest.mark.asyncio
    async def test_async_set_ndi_enabled_true(self) -> None:
        """Test enabling NDI stream."""
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

        await client.async_set_ndi_enabled(True)

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["data"]["switch"] == 1

    @pytest.mark.asyncio
    async def test_async_set_ndi_enabled_false(self) -> None:
        """Test disabling NDI stream."""
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

        await client.async_set_ndi_enabled(False)

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["data"]["switch"] == 0

    @pytest.mark.asyncio
    async def test_async_set_stream_enabled_rtmp_true(self) -> None:
        """Test enabling RTMP stream."""
        # First call returns publish list with RTMP entry
        mock_response_get = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "publish": [
                    {"type": "rtmp", "index": 0, "switch": 0, "url": "rtmp://example.com"},
                ],
            }
        )
        # Second call is the setinfo
        mock_response_set = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )

        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()

        # Return different responses for each call
        call_count = [0]

        def create_context_manager(response: MagicMock) -> MagicMock:
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=response)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            call_count[0] += 1
            if call_count[0] == 1:
                return create_context_manager(mock_response_get)
            return create_context_manager(mock_response_set)

        mock_session.post = MagicMock(side_effect=side_effect)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_stream_enabled("rtmp", True)

        assert mock_session.post.call_count == 2
        # Second call is the setinfo with update_publish_switch
        call_args = mock_session.post.call_args_list[1]
        json_data = call_args[1]["json"]
        assert json_data["opt"] == "update_publish_switch"
        assert json_data["data"]["index"] == 0
        assert json_data["data"]["switch"] == 1

    @pytest.mark.asyncio
    async def test_async_set_stream_enabled_srt_false(self) -> None:
        """Test disabling SRT stream."""
        # First call returns publish list with SRT entry
        mock_response_get = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "publish": [
                    {"type": "rtmp", "index": 0, "switch": 1, "url": "rtmp://example.com"},
                    {"type": "srt", "index": 1, "switch": 1, "url": "srt://example.com"},
                ],
            }
        )
        # Second call is the setinfo
        mock_response_set = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )

        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()

        call_count = [0]

        def create_context_manager(response: MagicMock) -> MagicMock:
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=response)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            call_count[0] += 1
            if call_count[0] == 1:
                return create_context_manager(mock_response_get)
            return create_context_manager(mock_response_set)

        mock_session.post = MagicMock(side_effect=side_effect)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_stream_enabled("srt", False)

        assert mock_session.post.call_count == 2
        # Second call is the setinfo with update_publish_switch
        call_args = mock_session.post.call_args_list[1]
        json_data = call_args[1]["json"]
        assert json_data["opt"] == "update_publish_switch"
        assert json_data["data"]["index"] == 1
        assert json_data["data"]["switch"] == 0

    @pytest.mark.asyncio
    async def test_async_set_stream_enabled_not_found(self) -> None:
        """Test error when stream type not found."""
        # Return empty publish list
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

        with pytest.raises(ZowietekApiError) as exc_info:
            await client.async_set_stream_enabled("rtmp", True)

        assert "not found" in str(exc_info.value)


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


class TestZowietekClientVencInfo:
    """Tests for ZowietekClient venc info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_venc_info_success(self) -> None:
        """Test successful venc info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "venc": [
                    {
                        "venc_chnid": 0,
                        "codec": {"selected_id": 0, "codec_list": ["H.264", "H.265"]},
                        "bitrate": 12000000,
                        "width": 1920,
                        "height": 1080,
                        "framerate": 60,
                        "desc": "main",
                    },
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

        result = await client.async_get_venc_info()

        assert "venc" in result
        assert len(result["venc"]) == 1
        assert result["venc"][0]["width"] == 1920


class TestZowietekClientAudioInfo:
    """Tests for ZowietekClient audio info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_audio_info_success(self) -> None:
        """Test successful audio info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "all": {
                    "switch": 1,
                    "ai_type": {
                        "selected_id": 0,
                        "ai_type_list": ["LINE IN", "HDMI IN"],
                    },
                    "volume": 100,
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

        result = await client.async_get_audio_info()

        assert result["switch"] == 1
        assert result["volume"] == 100


class TestZowietekClientSysAttrInfo:
    """Tests for ZowietekClient sys attr info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_sys_attr_info_success(self) -> None:
        """Test successful sys attr info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "SN": "ZBOX-12345",
                    "device_name": "ZowieBox-Studio",
                    "firmware_version": "1.2.3",
                    "hardware_version": "2.0",
                    "model": "ZowieBox-4K",
                    "manufacturer": "Zowietek",
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

        result = await client.async_get_sys_attr_info()

        assert result["SN"] == "ZBOX-12345"
        assert result["firmware_version"] == "1.2.3"


class TestZowietekClientDashboardInfo:
    """Tests for ZowietekClient dashboard info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_dashboard_info_success(self) -> None:
        """Test successful dashboard info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "persistent_time": "02:30:15",
                    "device_strat_time": "2025-11-30 10:00:00",
                    "cpu_temp": 45.5,
                    "cpu_payload": 25.0,
                    "memory_info": {
                        "used": 512,
                        "total": 1024,
                    },
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

        result = await client.async_get_dashboard_info()

        assert result["persistent_time"] == "02:30:15"
        assert result["cpu_temp"] == 45.5


class TestZowietekClientEncoderCodecSetter:
    """Tests for ZowietekClient encoder codec setter."""

    @pytest.mark.asyncio
    async def test_async_set_encoder_codec_success(self) -> None:
        """Test successful encoder codec setting."""
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

        await client.async_set_encoder_codec(1)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "venc"
        assert json_data["venc"][0]["codec"]["selected_id"] == 1
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_set_encoder_codec_auth_failure(self) -> None:
        """Test encoder codec setting with auth failure."""
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
            password="wrong",
            session=mock_session,
        )

        with pytest.raises(ZowietekAuthError):
            await client.async_set_encoder_codec(1)


class TestZowietekClientNdiModeSetter:
    """Tests for ZowietekClient NDI mode setter."""

    @pytest.mark.asyncio
    async def test_async_set_ndi_mode_success(self) -> None:
        """Test successful NDI mode setting."""
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

        await client.async_set_ndi_mode(3)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "ndi"
        assert json_data["opt"] == "set_ndi_info"
        assert json_data["data"]["mode_id"] == 3
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_set_ndi_mode_auth_failure(self) -> None:
        """Test NDI mode setting with auth failure."""
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
            password="wrong",
            session=mock_session,
        )

        with pytest.raises(ZowietekAuthError):
            await client.async_set_ndi_mode(3)


class TestZowietekClientMppRestartStatus:
    """Tests for ZowietekClient handling of MPP restart status code.

    The ZowieBox device returns status 10000 with "mpp restart..." when
    the media processing pipeline needs to restart after a codec change.
    This should be treated as a successful operation.
    """

    @pytest.mark.asyncio
    async def test_mpp_restart_status_treated_as_success(self) -> None:
        """Test that status 10000 with 'mpp restart' is treated as success."""
        mock_response = _create_mock_response(
            {
                "status": "10000",
                "rsp": "mpp restart...",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        # This should NOT raise an exception
        await client.async_set_encoder_codec(1)

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_mpp_restart_status_with_ndi_mode(self) -> None:
        """Test that status 10000 is handled for NDI mode changes too."""
        mock_response = _create_mock_response(
            {
                "status": "10000",
                "rsp": "mpp restart...",
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        # This should NOT raise an exception
        await client.async_set_ndi_mode(3)

        mock_session.post.assert_called_once()


class TestZowietekClientRebootEmptyResponse:
    """Tests for ZowietekClient handling of empty reboot response.

    When a reboot command is issued, the device may close the connection
    before sending a response. This should be handled gracefully.
    """

    @pytest.mark.asyncio
    async def test_reboot_with_empty_response(self) -> None:
        """Test that empty response during reboot is handled gracefully."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock(), message="Empty response")
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

        # This should NOT raise an exception for reboot
        await client.async_reboot()

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_reboot_with_json_decode_error(self) -> None:
        """Test that JSONDecodeError during reboot is handled gracefully."""
        import json

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "", 0))

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

        # This should NOT raise an exception for reboot
        await client.async_reboot()

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_reboot_with_connection_reset(self) -> None:
        """Test that connection reset during reboot is handled gracefully."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.post = MagicMock(side_effect=aiohttp.ClientConnectionError("Connection reset"))

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        # This should NOT raise an exception for reboot
        await client.async_reboot()

        mock_session.post.assert_called_once()


class TestZowietekClientAudioVolumeSetter:
    """Tests for ZowietekClient audio volume setter."""

    @pytest.mark.asyncio
    async def test_async_set_audio_volume_success(self) -> None:
        """Test successful audio volume setting."""
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

        await client.async_set_audio_volume(75)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "audio"
        assert json_data["volume"] == 75
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_set_audio_volume_auth_failure(self) -> None:
        """Test audio volume setting with auth failure."""
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
            password="wrong",
            session=mock_session,
        )

        with pytest.raises(ZowietekAuthError):
            await client.async_set_audio_volume(50)


class TestZowietekClientEncoderBitrateSetter:
    """Tests for ZowietekClient encoder bitrate setter."""

    @pytest.mark.asyncio
    async def test_async_set_encoder_bitrate_success(self) -> None:
        """Test successful encoder bitrate setting."""
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

        await client.async_set_encoder_bitrate(12000000)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "venc"
        assert json_data["venc"][0]["bitrate"] == 12000000
        assert json_data["venc"][0]["venc_chnid"] == 0
        assert json_data["venc"][0]["desc"] == "main"
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_set_encoder_bitrate_auth_failure(self) -> None:
        """Test encoder bitrate setting with auth failure."""
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
            password="wrong",
            session=mock_session,
        )

        with pytest.raises(ZowietekAuthError):
            await client.async_set_encoder_bitrate(8000000)


class TestZowietekClientSetNdiSettings:
    """Tests for ZowietekClient NDI settings setter."""

    @pytest.mark.asyncio
    async def test_async_set_ndi_settings_name_only(self) -> None:
        """Test setting NDI settings with name only.

        The API first gets current config, then sends complete structure with changes.
        When only name is provided, the existing group is preserved.
        """
        # First response: get current NDI config
        get_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "switch": 1,
                    "mode_id": 3,
                    "machinename": "OldName",
                    "groups": "ExistingGroup",
                    "multicast": {
                        "ttl": 1,
                        "enable": 0,
                        "netmask": "255.255.0.0",
                        "netprefix": "239.255.0.0",
                    },
                },
            }
        )
        # Second response: set NDI config
        set_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )
        mock_session = _create_mock_session(get_response)
        # Set up side_effect to return different responses for each call
        mock_session.post.return_value.__aenter__.side_effect = [
            get_response,
            set_response,
        ]

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_ndi_settings(name="MyNDISource")

        # Check that two calls were made
        assert mock_session.post.call_count == 2

        # Check the set call (second call)
        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "ndi"
        assert json_data["opt"] == "set_ndi_info"
        assert json_data["data"]["machinename"] == "MyNDISource"
        # Existing group should be preserved
        assert json_data["data"]["groups"] == "ExistingGroup"
        # Other fields from current config should be preserved
        assert json_data["data"]["switch"] == 1
        assert json_data["data"]["mode_id"] == 3
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_set_ndi_settings_with_group(self) -> None:
        """Test setting NDI settings with name and group.

        When group is provided, it should override the existing group.
        """
        # First response: get current NDI config
        get_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "switch": 0,
                    "mode_id": 1,
                    "machinename": "OldName",
                    "groups": "OldGroup",
                    "multicast": {
                        "ttl": 1,
                        "enable": 0,
                        "netmask": "255.255.0.0",
                        "netprefix": "239.255.0.0",
                    },
                },
            }
        )
        # Second response: set NDI config
        set_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )
        mock_session = _create_mock_session(get_response)
        mock_session.post.return_value.__aenter__.side_effect = [
            get_response,
            set_response,
        ]

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_set_ndi_settings(name="MyNDISource", group="Production")

        # Check that two calls were made
        assert mock_session.post.call_count == 2

        # Check the set call (second call)
        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "ndi"
        assert json_data["opt"] == "set_ndi_info"
        assert json_data["data"]["machinename"] == "MyNDISource"
        # Group should be the new value
        assert json_data["data"]["groups"] == "Production"


class TestZowietekClientSetRtmpUrl:
    """Tests for ZowietekClient RTMP URL setter."""

    @pytest.mark.asyncio
    async def test_async_set_rtmp_url_without_key(self) -> None:
        """Test setting RTMP URL without stream key."""
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

        await client.async_set_rtmp_url(url="rtmp://live.example.com/live")

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "publish"
        assert json_data["opt"] == "update_publish_url"
        assert json_data["data"]["url"] == "rtmp://live.example.com/live"
        assert json_data["data"]["type"] == "rtmp"
        assert json_data["data"]["index"] == 0
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_set_rtmp_url_with_key(self) -> None:
        """Test setting RTMP URL with stream key."""
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

        await client.async_set_rtmp_url(url="rtmp://live.example.com/live", key="mykey")

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["data"]["url"] == "rtmp://live.example.com/live/mykey"


class TestZowietekClientSetSrtSettings:
    """Tests for ZowietekClient SRT settings setter."""

    @pytest.mark.asyncio
    async def test_async_set_srt_settings_port_only(self) -> None:
        """Test setting SRT settings with port only."""
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

        await client.async_set_srt_settings(port=9000)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "publish"
        assert json_data["opt"] == "update_srt_info"
        assert json_data["data"]["port"] == 9000
        assert json_data["data"]["type"] == "srt"
        assert json_data["data"]["index"] == 1
        assert "latency" not in json_data["data"]
        assert "passphrase" not in json_data["data"]
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_set_srt_settings_with_latency(self) -> None:
        """Test setting SRT settings with port and latency."""
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

        await client.async_set_srt_settings(port=9000, latency=120)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["data"]["port"] == 9000
        assert json_data["data"]["latency"] == 120
        assert "passphrase" not in json_data["data"]

    @pytest.mark.asyncio
    async def test_async_set_srt_settings_with_all_params(self) -> None:
        """Test setting SRT settings with all parameters."""
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

        await client.async_set_srt_settings(port=9000, latency=120, passphrase="secretkey")

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["data"]["port"] == 9000
        assert json_data["data"]["latency"] == 120
        assert json_data["data"]["passphrase"] == "secretkey"
