"""Tests for ZowietekClient streamplay/decoder API methods."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.zowietek.api import ZowietekClient
from custom_components.zowietek.const import STATUS_SUCCESS
from custom_components.zowietek.exceptions import (
    ZowietekAuthError,
)


def _create_mock_response(
    data: dict[str, Any],
    status: int = 200,
) -> MagicMock:
    """Create a mock aiohttp response with context manager support."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=data)
    return mock_response


def _create_mock_session(
    response: MagicMock | Exception,
) -> MagicMock:
    """Create a mock aiohttp session with context manager support."""
    mock_session = MagicMock(spec=aiohttp.ClientSession)
    mock_session.closed = False
    mock_session.close = AsyncMock()

    if isinstance(response, Exception):
        mock_session.post = MagicMock(side_effect=response)
    else:
        context_manager = MagicMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=context_manager)

    return mock_session


class TestZowietekClientStreamplayInfo:
    """Tests for ZowietekClient streamplay info endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_streamplay_info_success(self) -> None:
        """Test successful streamplay info retrieval."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "streamplay": [
                        {
                            "index": 0,
                            "switch": 1,
                            "name": "Test Stream",
                            "streamtype": 1,
                            "url": "rtsp://example.com/stream",
                            "streamplay_status": 1,
                            "bandwidth": 5000,
                            "framerate": 30,
                            "width": 1920,
                            "height": 1080,
                        },
                    ],
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

        result = await client.async_get_streamplay_info()

        assert "streamplay" in result
        assert len(result["streamplay"]) == 1
        assert result["streamplay"][0]["name"] == "Test Stream"
        assert result["streamplay"][0]["url"] == "rtsp://example.com/stream"

    @pytest.mark.asyncio
    async def test_async_get_streamplay_info_empty(self) -> None:
        """Test streamplay info when no streams configured."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "streamplay": [],
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

        result = await client.async_get_streamplay_info()

        assert result["streamplay"] == []

    @pytest.mark.asyncio
    async def test_async_get_streamplay_info_multiple_sources(self) -> None:
        """Test streamplay info with multiple configured sources."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "streamplay": [
                        {
                            "index": 0,
                            "switch": 0,
                            "name": "RTSP Stream",
                            "streamtype": 1,
                            "url": "rtsp://camera1.local/live",
                        },
                        {
                            "index": 1,
                            "switch": 1,
                            "name": "SRT Input",
                            "streamtype": 1,
                            "url": "srt://192.168.1.50:9000",
                        },
                    ],
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

        result = await client.async_get_streamplay_info()

        assert len(result["streamplay"]) == 2
        assert result["streamplay"][0]["name"] == "RTSP Stream"
        assert result["streamplay"][1]["name"] == "SRT Input"

    @pytest.mark.asyncio
    async def test_async_get_streamplay_info_data_as_list(self) -> None:
        """Test streamplay info when API returns data as a list (live device format).

        Some firmware versions return the sources directly in 'data' as a list
        rather than nested under 'data.streamplay'.
        """
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": [
                    {
                        "index": 2,
                        "switch": 1,
                        "name": "Sydney",
                        "streamtype": 1,
                        "url": "rtsp://live.example.com/stream",
                        "streamplay_status": 1,
                    },
                ],
                "streamplay": [],  # Empty in this format
            }
        )
        mock_session = _create_mock_session(mock_response)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        result = await client.async_get_streamplay_info()

        assert "streamplay" in result
        assert len(result["streamplay"]) == 1
        assert result["streamplay"][0]["name"] == "Sydney"
        assert result["streamplay"][0]["index"] == 2


class TestZowietekClientDecoderStatus:
    """Tests for ZowietekClient decoder status endpoint."""

    @pytest.mark.asyncio
    async def test_async_get_decoder_status_playing(self) -> None:
        """Test decoder status when actively playing."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "decoder_state": 1,
                    "active_source": "Test Stream",
                    "width": 1920,
                    "height": 1080,
                    "framerate": 30,
                    "bandwidth": 5000,
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

        result = await client.async_get_decoder_status()

        assert result["decoder_state"] == 1
        assert result["active_source"] == "Test Stream"

    @pytest.mark.asyncio
    async def test_async_get_decoder_status_idle(self) -> None:
        """Test decoder status when idle (not playing)."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "decoder_state": 0,
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

        result = await client.async_get_decoder_status()

        assert result["decoder_state"] == 0


class TestZowietekClientAddDecodingUrl:
    """Tests for ZowietekClient add decoding URL endpoint."""

    @pytest.mark.asyncio
    async def test_async_add_decoding_url_success(self) -> None:
        """Test successfully adding a decoding URL."""
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

        await client.async_add_decoding_url(
            name="My Stream",
            url="rtsp://camera.local/stream",
            streamtype=1,
            switch=True,
        )

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "streamplay"
        assert json_data["opt"] == "streamplay_add"
        assert json_data["name"] == "My Stream"
        assert json_data["url"] == "rtsp://camera.local/stream"
        assert json_data["streamtype"] == 1
        assert json_data["switch"] == 1
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_add_decoding_url_disabled(self) -> None:
        """Test adding a decoding URL in disabled state."""
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

        await client.async_add_decoding_url(
            name="Backup Stream",
            url="srt://192.168.1.50:9000",
            streamtype=1,
            switch=False,
        )

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["switch"] == 0

    @pytest.mark.asyncio
    async def test_async_add_decoding_url_auth_failure(self) -> None:
        """Test adding decoding URL with auth failure."""
        mock_response = _create_mock_response(
            {
                "status": "80003",
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
            await client.async_add_decoding_url(
                name="My Stream",
                url="rtsp://camera.local/stream",
                streamtype=1,
                switch=True,
            )


class TestZowietekClientModifyDecodingUrl:
    """Tests for ZowietekClient modify decoding URL endpoint."""

    @pytest.mark.asyncio
    async def test_async_modify_decoding_url_success(self) -> None:
        """Test successfully modifying a decoding URL."""
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

        await client.async_modify_decoding_url(
            index=0,
            name="Updated Stream",
            url="rtsp://newcamera.local/stream",
            streamtype=1,
            switch=True,
        )

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "streamplay"
        assert json_data["opt"] == "streamplay_modify"
        assert json_data["index"] == 0
        assert json_data["name"] == "Updated Stream"
        assert json_data["url"] == "rtsp://newcamera.local/stream"
        assert json_data["user"] == "admin"


class TestZowietekClientDeleteDecodingUrl:
    """Tests for ZowietekClient delete decoding URL endpoint."""

    @pytest.mark.asyncio
    async def test_async_delete_decoding_url_success(self) -> None:
        """Test successfully deleting a decoding URL."""
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

        await client.async_delete_decoding_url(index=1)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "streamplay"
        assert json_data["opt"] == "streamplay_del"
        assert json_data["index"] == 1
        assert json_data["user"] == "admin"


class TestZowietekClientNdiDecoding:
    """Tests for ZowietekClient NDI decoding endpoints."""

    @pytest.mark.asyncio
    async def test_async_enable_ndi_decoding_success(self) -> None:
        """Test successfully enabling NDI decoding."""
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

        await client.async_enable_ndi_decoding(ndi_name="CAMERA1 (Channel 1)")

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "streamplay"
        assert json_data["opt"] == "ndi_enable"
        assert json_data["ndi_name"] == "CAMERA1 (Channel 1)"
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_disable_ndi_decoding_success(self) -> None:
        """Test successfully disabling NDI decoding."""
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

        await client.async_disable_ndi_decoding()

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "streamplay"
        assert json_data["opt"] == "ndi_close"
        assert json_data["user"] == "admin"


class TestZowietekClientNdiSources:
    """Tests for ZowietekClient NDI source discovery endpoints."""

    @pytest.mark.asyncio
    async def test_async_get_ndi_sources_success(self) -> None:
        """Test successfully getting NDI sources."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "ndi_sources": [
                        {
                            "index": 0,
                            "name": "CAMERA1 (Channel 1)",
                            "url": "CAMERA1 (Channel 1)",
                        },
                        {
                            "index": 1,
                            "name": "CAMERA2 (Channel 1)",
                            "url": "CAMERA2 (Channel 1)",
                        },
                    ],
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

        result = await client.async_get_ndi_sources()

        assert "ndi_sources" in result
        assert len(result["ndi_sources"]) == 2
        assert result["ndi_sources"][0]["name"] == "CAMERA1 (Channel 1)"

    @pytest.mark.asyncio
    async def test_async_get_ndi_sources_empty(self) -> None:
        """Test getting NDI sources when none available."""
        mock_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": {
                    "ndi_sources": [],
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

        result = await client.async_get_ndi_sources()

        assert result["ndi_sources"] == []

    @pytest.mark.asyncio
    async def test_async_ndi_find_success(self) -> None:
        """Test triggering NDI source discovery."""
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

        await client.async_ndi_find()

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "streamplay"
        assert json_data["opt"] == "ndi_find"


class TestZowietekClientSelectStreamplaySource:
    """Tests for ZowietekClient streamplay source selection."""

    @pytest.mark.asyncio
    async def test_async_select_streamplay_source_success(self) -> None:
        """Test successfully selecting a streamplay source."""
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

        await client.async_select_streamplay_source(index=0)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["group"] == "streamplay"
        assert json_data["opt"] == "streamplay_switch"
        assert json_data["data"]["index"] == 0
        assert json_data["data"]["switch"] == 1
        assert json_data["user"] == "admin"

    @pytest.mark.asyncio
    async def test_async_select_streamplay_source_different_index(self) -> None:
        """Test selecting a different streamplay source by index."""
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

        await client.async_select_streamplay_source(index=2)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["data"]["index"] == 2
        assert json_data["data"]["switch"] == 1


class TestZowietekClientStopStreamplay:
    """Tests for ZowietekClient streamplay stop."""

    @pytest.mark.asyncio
    async def test_async_stop_streamplay_success(self) -> None:
        """Test successfully stopping streamplay when a source is active."""
        # Create responses for both API calls: get_streamplay_info and stop
        get_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": [
                    {"index": 0, "switch": 0, "name": "Source 1"},
                    {"index": 1, "switch": 1, "name": "Active Source"},  # Active
                    {"index": 2, "switch": 0, "name": "Source 3"},
                ],
            }
        )
        stop_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
            }
        )

        # Set up mock to return different responses for each call
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()

        # Create context managers for each call
        get_cm = MagicMock()
        get_cm.__aenter__ = AsyncMock(return_value=get_response)
        get_cm.__aexit__ = AsyncMock(return_value=None)

        stop_cm = MagicMock()
        stop_cm.__aenter__ = AsyncMock(return_value=stop_response)
        stop_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.post = MagicMock(side_effect=[get_cm, stop_cm])

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_stop_streamplay()

        # Should have made 2 calls: get info, then stop
        assert mock_session.post.call_count == 2

        # Verify the stop call used the correct index
        stop_call_args = mock_session.post.call_args_list[1]
        json_data = stop_call_args[1]["json"]
        assert json_data["group"] == "streamplay"
        assert json_data["opt"] == "streamplay_switch"
        assert json_data["data"]["index"] == 1  # The active source index
        assert json_data["data"]["switch"] == 0  # Disable it

    @pytest.mark.asyncio
    async def test_async_stop_streamplay_no_active_source(self) -> None:
        """Test stopping streamplay when no source is active does nothing."""
        get_response = _create_mock_response(
            {
                "status": STATUS_SUCCESS,
                "rsp": "succeed",
                "data": [
                    {"index": 0, "switch": 0, "name": "Source 1"},
                    {"index": 1, "switch": 0, "name": "Source 2"},
                ],
            }
        )

        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()

        get_cm = MagicMock()
        get_cm.__aenter__ = AsyncMock(return_value=get_response)
        get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.post = MagicMock(return_value=get_cm)

        client = ZowietekClient(
            host="192.168.1.100",
            username="admin",
            password="admin",
            session=mock_session,
        )

        await client.async_stop_streamplay()

        # Should only have made 1 call (get info), no stop call needed
        assert mock_session.post.call_count == 1
