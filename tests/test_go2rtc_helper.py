"""Tests for the go2rtc helper module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.zowietek.const import (
    GO2RTC_DEFAULT_API_URL,
    GO2RTC_DEFAULT_RTSP_PORT,
    GO2RTC_DOMAIN,
    GO2RTC_EXTERNAL_RTSP_PORT,
    GO2RTC_STREAM_PREFIX,
    GO2RTC_STREAM_TTL,
)
from custom_components.zowietek.go2rtc_helper import Go2rtcHelper, ManagedStream

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_hass_with_go2rtc() -> MagicMock:
    """Create a mock Home Assistant instance with go2rtc available (localhost)."""
    hass = MagicMock(spec=HomeAssistant)
    # Mock the go2rtc config with localhost URL (HA-managed)
    go2rtc_config = MagicMock()
    go2rtc_config.url = "http://127.0.0.1:11984/"
    hass.data = {GO2RTC_DOMAIN: go2rtc_config}
    hass.states = MagicMock()
    return hass


@pytest.fixture
def mock_hass_with_external_go2rtc() -> MagicMock:
    """Create a mock Home Assistant instance with external go2rtc server."""
    hass = MagicMock(spec=HomeAssistant)
    # Mock the go2rtc config with external URL
    go2rtc_config = MagicMock()
    go2rtc_config.url = "http://frigate.example.com:1984"
    hass.data = {GO2RTC_DOMAIN: go2rtc_config}
    hass.states = MagicMock()
    return hass


@pytest.fixture
def mock_hass_without_go2rtc() -> MagicMock:
    """Create a mock Home Assistant instance without go2rtc."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.states = MagicMock()
    return hass


@pytest.fixture
def mock_aiohttp_session() -> Generator[MagicMock]:
    """Mock aiohttp ClientSession."""
    with (
        patch(
            "custom_components.zowietek.go2rtc_helper.aiohttp.ClientSession"
        ) as mock_session_class,
        patch(
            "custom_components.zowietek.go2rtc_helper.get_url",
            return_value="http://127.0.0.1:8123",
        ),
    ):
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Default successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.text = AsyncMock(return_value="OK")

        mock_session.put = MagicMock(return_value=mock_response)
        mock_session.delete = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        yield mock_session


class TestGo2rtcHelperAvailability:
    """Tests for go2rtc availability detection."""

    def test_is_available_when_go2rtc_present(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test is_available returns True when go2rtc is in hass.data."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)
        assert helper.is_available is True

    def test_is_available_when_go2rtc_absent(
        self,
        mock_hass_without_go2rtc: MagicMock,
    ) -> None:
        """Test is_available returns False when go2rtc is not in hass.data."""
        helper = Go2rtcHelper(mock_hass_without_go2rtc)
        assert helper.is_available is False


class TestGo2rtcHelperLifecycle:
    """Tests for helper lifecycle management."""

    async def test_async_start_creates_cleanup_task(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test async_start creates the cleanup task."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        assert helper._cleanup_task is None
        await helper.async_start()
        assert helper._cleanup_task is not None

        # Cleanup
        await helper.async_stop()

    async def test_async_stop_cancels_cleanup_task(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test async_stop cancels the cleanup task."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        await helper.async_start()
        assert helper._cleanup_task is not None

        await helper.async_stop()
        assert helper._cleanup_task is None

    async def test_async_stop_closes_session(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test async_stop closes the aiohttp session."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Trigger session creation by converting a stream
        await helper.async_convert_stream("rtsp://test.stream/live")

        await helper.async_stop()

        mock_aiohttp_session.close.assert_called_once()


class TestGo2rtcHelperStreamConversion:
    """Tests for stream URL conversion."""

    async def test_convert_stream_returns_none_when_unavailable(
        self,
        mock_hass_without_go2rtc: MagicMock,
    ) -> None:
        """Test convert_stream returns None when go2rtc is unavailable."""
        helper = Go2rtcHelper(mock_hass_without_go2rtc)

        result = await helper.async_convert_stream("http://example.com/stream.m3u8")

        assert result is None

    async def test_convert_stream_success(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test successful stream conversion returns RTSP URL."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        source_url = "http://example.com/stream.m3u8"
        result = await helper.async_convert_stream(source_url)

        assert result is not None
        assert result.startswith(f"rtsp://127.0.0.1:{GO2RTC_DEFAULT_RTSP_PORT}/")
        assert GO2RTC_STREAM_PREFIX in result

        await helper.async_stop()

    async def test_convert_stream_generates_consistent_name(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test stream name is consistent for the same URL."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        source_url = "http://example.com/stream.m3u8"
        result1 = await helper.async_convert_stream(source_url)
        result2 = await helper.async_convert_stream(source_url)

        assert result1 == result2

        await helper.async_stop()

    async def test_convert_stream_different_urls_different_names(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test different URLs produce different stream names."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        result1 = await helper.async_convert_stream("http://example.com/stream1.m3u8")
        result2 = await helper.async_convert_stream("http://example.com/stream2.m3u8")

        assert result1 != result2

        await helper.async_stop()

    async def test_convert_stream_reuses_existing(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test converting same URL reuses cached stream without API call."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        source_url = "http://example.com/stream.m3u8"

        # First call - should hit API
        await helper.async_convert_stream(source_url)
        call_count_after_first = mock_aiohttp_session.put.call_count

        # Second call - should use cache
        await helper.async_convert_stream(source_url)
        call_count_after_second = mock_aiohttp_session.put.call_count

        # API should only be called once
        assert call_count_after_first == call_count_after_second

        await helper.async_stop()

    async def test_convert_stream_updates_last_accessed(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test converting cached stream updates last_accessed time."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        source_url = "http://example.com/stream.m3u8"

        # First conversion
        await helper.async_convert_stream(source_url)

        # Get the stream name from the helper's internal state
        stream_names = list(helper._streams.keys())
        assert len(stream_names) == 1
        stream_name = stream_names[0]

        original_time = helper._streams[stream_name].last_accessed

        # Small delay
        await asyncio.sleep(0.01)

        # Second conversion should update last_accessed
        await helper.async_convert_stream(source_url)

        updated_time = helper._streams[stream_name].last_accessed
        assert updated_time > original_time

        await helper.async_stop()

    async def test_convert_stream_api_error_returns_none(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test API error during conversion returns None."""
        # Make the API return an error
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_aiohttp_session.put.return_value = mock_response

        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        result = await helper.async_convert_stream("http://example.com/stream.m3u8")

        assert result is None

        await helper.async_stop()


class TestGo2rtcHelperCameraConversion:
    """Tests for camera entity conversion."""

    async def test_convert_camera_returns_none_when_unavailable(
        self,
        mock_hass_without_go2rtc: MagicMock,
    ) -> None:
        """Test convert_camera returns None when go2rtc is unavailable."""
        helper = Go2rtcHelper(mock_hass_without_go2rtc)

        result = await helper.async_convert_camera("camera.front_door")

        assert result is None

    async def test_convert_camera_returns_none_when_entity_not_found(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test convert_camera returns None when camera entity doesn't exist."""
        mock_hass_with_go2rtc.states.get.return_value = None

        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        result = await helper.async_convert_camera("camera.nonexistent")

        assert result is None

    async def test_convert_camera_success(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test successful camera entity conversion."""
        # Mock camera entity exists
        mock_state = MagicMock()
        mock_state.entity_id = "camera.front_door"
        mock_hass_with_go2rtc.states.get.return_value = mock_state

        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        result = await helper.async_convert_camera("camera.front_door")

        assert result is not None
        assert result.startswith(f"rtsp://127.0.0.1:{GO2RTC_DEFAULT_RTSP_PORT}/")

        # Verify the ffmpeg source was used
        call_args = mock_aiohttp_session.put.call_args
        assert "ffmpeg:camera.front_door" in str(call_args)

        await helper.async_stop()


class TestGo2rtcHelperStreamCleanup:
    """Tests for TTL-based stream cleanup."""

    async def test_cleanup_removes_inactive_streams(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test cleanup removes streams that exceed TTL."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Add a stream
        source_url = "http://example.com/stream.m3u8"
        await helper.async_convert_stream(source_url)

        # Verify stream exists
        assert len(helper._streams) == 1

        # Manually set last_accessed to be older than TTL
        stream_name = next(iter(helper._streams.keys()))
        helper._streams[stream_name].last_accessed = datetime.now() - timedelta(
            seconds=GO2RTC_STREAM_TTL + 60
        )

        # Run cleanup
        await helper._cleanup_inactive_streams()

        # Stream should be removed
        assert len(helper._streams) == 0

        # Delete should have been called
        mock_aiohttp_session.delete.assert_called_once()

        await helper.async_stop()

    async def test_cleanup_keeps_active_streams(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test cleanup keeps streams that are still within TTL."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Add a stream (will have current timestamp)
        source_url = "http://example.com/stream.m3u8"
        await helper.async_convert_stream(source_url)

        # Verify stream exists
        assert len(helper._streams) == 1

        # Run cleanup
        await helper._cleanup_inactive_streams()

        # Stream should still exist
        assert len(helper._streams) == 1

        # Delete should not have been called
        mock_aiohttp_session.delete.assert_not_called()

        await helper.async_stop()

    async def test_cleanup_all_streams_on_stop(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test all streams are cleaned up when helper stops."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Add multiple streams
        await helper.async_convert_stream("http://example.com/stream1.m3u8")
        await helper.async_convert_stream("http://example.com/stream2.m3u8")
        await helper.async_convert_stream("http://example.com/stream3.m3u8")

        assert len(helper._streams) == 3

        # Stop the helper
        await helper.async_stop()

        # All streams should be removed
        assert len(helper._streams) == 0

        # Delete should have been called for each stream
        assert mock_aiohttp_session.delete.call_count == 3


class TestGo2rtcHelperApiCalls:
    """Tests for go2rtc API interactions."""

    async def test_add_stream_calls_correct_endpoint(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test _add_stream calls the correct go2rtc API endpoint."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        source_url = "http://example.com/stream.m3u8"
        await helper.async_convert_stream(source_url)

        # Verify PUT was called with correct URL (uses config URL)
        call_args = mock_aiohttp_session.put.call_args
        url = call_args[0][0]
        assert "http://127.0.0.1:11984/api/streams" in url

        await helper.async_stop()

    async def test_delete_stream_calls_correct_endpoint(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test _delete_stream calls the correct go2rtc API endpoint."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Add then remove a stream
        await helper.async_convert_stream("http://example.com/stream.m3u8")

        # Manually trigger cleanup of all streams
        await helper._cleanup_all_streams()

        # Verify DELETE was called with correct URL (uses config URL)
        call_args = mock_aiohttp_session.delete.call_args
        url = call_args[0][0]
        assert "http://127.0.0.1:11984/api/streams" in url

        await helper.async_stop()

    async def test_delete_stream_handles_404_gracefully(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test _delete_stream handles 404 (stream not found) gracefully."""
        # Make delete return 404
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_aiohttp_session.delete.return_value = mock_response

        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Add a stream
        await helper.async_convert_stream("http://example.com/stream.m3u8")

        # Cleanup should not raise even with 404
        await helper._cleanup_all_streams()

        # Streams dict should be cleared
        assert len(helper._streams) == 0

        await helper.async_stop()


class TestManagedStreamDataclass:
    """Tests for the ManagedStream dataclass."""

    def test_managed_stream_creation(self) -> None:
        """Test ManagedStream can be created with required fields."""
        stream = ManagedStream(
            name="test_stream",
            source_url="http://example.com/stream.m3u8",
            rtsp_url="rtsp://127.0.0.1:18554/test_stream",
        )

        assert stream.name == "test_stream"
        assert stream.source_url == "http://example.com/stream.m3u8"
        assert stream.rtsp_url == "rtsp://127.0.0.1:18554/test_stream"
        assert stream.last_accessed is not None

    def test_managed_stream_default_last_accessed(self) -> None:
        """Test ManagedStream has default last_accessed timestamp."""
        before = datetime.now()

        stream = ManagedStream(
            name="test_stream",
            source_url="http://example.com/stream.m3u8",
            rtsp_url="rtsp://127.0.0.1:18554/test_stream",
        )

        after = datetime.now()

        assert before <= stream.last_accessed <= after


class TestGo2rtcHelperEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_delete_stream_without_session(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _delete_stream returns early when session is None."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Session is None by default
        assert helper._session is None

        # Should not raise
        await helper._delete_stream("nonexistent_stream")

    async def test_delete_stream_non_200_404_status(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test _delete_stream logs warning on unexpected status code."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # First add a stream to initialize session
        await helper.async_convert_stream("http://example.com/stream.m3u8")

        # Now make delete return 500
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_aiohttp_session.delete.return_value = mock_response

        # Should not raise, but should log warning
        await helper._delete_stream("test_stream")

        await helper.async_stop()

    async def test_delete_stream_with_exception(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test _delete_stream handles exceptions gracefully."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # First add a stream to initialize session
        await helper.async_convert_stream("http://example.com/stream.m3u8")

        # Make delete raise an exception
        mock_aiohttp_session.delete.side_effect = Exception("Connection refused")

        # Should not raise
        await helper._delete_stream("test_stream")

        await helper.async_stop()

    async def test_cleanup_loop_runs_periodically(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test cleanup loop runs and can be cancelled."""

        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Start the helper (starts cleanup task)
        await helper.async_start()
        assert helper._cleanup_task is not None
        assert not helper._cleanup_task.done()

        # Stop the helper (cancels cleanup task)
        await helper.async_stop()
        assert helper._cleanup_task is None

    async def test_cleanup_loop_executes_cleanup(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test cleanup loop actually executes the cleanup method."""
        import asyncio

        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Add a stream to clean up
        await helper.async_convert_stream("http://example.com/stream.m3u8")
        assert len(helper._streams) == 1

        # Make the stream old enough to be cleaned up
        stream_name = next(iter(helper._streams.keys()))
        helper._streams[stream_name].last_accessed = datetime.now() - timedelta(
            seconds=GO2RTC_STREAM_TTL + 60
        )

        # Patch asyncio.sleep to return immediately
        with patch(
            "custom_components.zowietek.go2rtc_helper.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            # Make sleep raise CancelledError after first call
            # to exit the infinite loop
            mock_sleep.side_effect = [None, asyncio.CancelledError()]

            # Run the cleanup loop directly
            with pytest.raises(asyncio.CancelledError):
                await helper._cleanup_loop()

            # Verify cleanup was called (stream should be removed)
            assert len(helper._streams) == 0

        await helper.async_stop()


class TestGo2rtcHelperHostResolution:
    """Tests for HA host address resolution."""

    async def test_get_ha_host_returns_internal_url_host(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _get_ha_host returns hostname from internal URL."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        with patch(
            "custom_components.zowietek.go2rtc_helper.get_url",
            return_value="http://192.168.1.100:8123",
        ):
            host = helper._get_ha_host()
            assert host == "192.168.1.100"

    async def test_get_ha_host_handles_hostname(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _get_ha_host works with hostname instead of IP."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        with patch(
            "custom_components.zowietek.go2rtc_helper.get_url",
            return_value="http://homeassistant.local:8123",
        ):
            host = helper._get_ha_host()
            assert host == "homeassistant.local"

    async def test_get_ha_host_fallback_on_no_url(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _get_ha_host falls back to 127.0.0.1 when no URL available."""
        from homeassistant.helpers.network import NoURLAvailableError

        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        with patch(
            "custom_components.zowietek.go2rtc_helper.get_url",
            side_effect=NoURLAvailableError,
        ):
            host = helper._get_ha_host()
            assert host == "127.0.0.1"

    async def test_convert_stream_uses_ha_host(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test async_convert_stream uses HA host in RTSP URL."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        with patch(
            "custom_components.zowietek.go2rtc_helper.get_url",
            return_value="http://192.168.1.50:8123",
        ):
            rtsp_url = await helper.async_convert_stream("http://example.com/stream.m3u8")

            assert rtsp_url is not None
            assert "192.168.1.50" in rtsp_url
            assert rtsp_url.startswith("rtsp://192.168.1.50:")

        await helper.async_stop()

    def test_format_host_for_url_ipv4(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _format_host_for_url leaves IPv4 addresses unchanged."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        assert helper._format_host_for_url("192.168.1.100") == "192.168.1.100"
        assert helper._format_host_for_url("10.0.0.1") == "10.0.0.1"
        assert helper._format_host_for_url("127.0.0.1") == "127.0.0.1"

    def test_format_host_for_url_hostname(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _format_host_for_url leaves hostnames unchanged."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        assert helper._format_host_for_url("homeassistant.local") == "homeassistant.local"
        assert helper._format_host_for_url("my-server.example.com") == "my-server.example.com"

    def test_format_host_for_url_ipv6(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _format_host_for_url wraps IPv6 addresses in brackets."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Standard IPv6 addresses should be wrapped
        assert helper._format_host_for_url("::1") == "[::1]"
        assert helper._format_host_for_url("fe80::1") == "[fe80::1]"
        assert helper._format_host_for_url("2001:db8::1") == "[2001:db8::1]"
        assert helper._format_host_for_url("fd00:1234:5678:9abc::1") == "[fd00:1234:5678:9abc::1]"

    def test_format_host_for_url_ipv6_already_bracketed(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _format_host_for_url doesn't double-bracket IPv6 addresses."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        # Already bracketed addresses should not be modified
        assert helper._format_host_for_url("[::1]") == "[::1]"
        assert helper._format_host_for_url("[fe80::1]") == "[fe80::1]"

    async def test_convert_stream_handles_ipv6(
        self,
        mock_hass_with_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test async_convert_stream properly formats IPv6 addresses in RTSP URL."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        with patch(
            "custom_components.zowietek.go2rtc_helper.get_url",
            return_value="http://[fd00::1]:8123",
        ):
            rtsp_url = await helper.async_convert_stream("http://example.com/stream.m3u8")

            assert rtsp_url is not None
            # IPv6 should be bracketed in the URL
            assert "[fd00::1]" in rtsp_url
            assert rtsp_url.startswith("rtsp://[fd00::1]:")

        await helper.async_stop()


class TestGo2rtcHelperExternalServer:
    """Tests for external go2rtc server configuration."""

    async def test_external_go2rtc_uses_configured_api_url(
        self,
        mock_hass_with_external_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test that external go2rtc server URL is used for API calls."""
        helper = Go2rtcHelper(mock_hass_with_external_go2rtc)

        source_url = "http://example.com/stream.m3u8"
        await helper.async_convert_stream(source_url)

        # Verify PUT was called with external server URL
        call_args = mock_aiohttp_session.put.call_args
        url = call_args[0][0]
        assert "http://frigate.example.com:1984/api/streams" in url

        await helper.async_stop()

    async def test_external_go2rtc_uses_external_rtsp_host(
        self,
        mock_hass_with_external_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test that external go2rtc returns RTSP URL with external host."""
        helper = Go2rtcHelper(mock_hass_with_external_go2rtc)

        source_url = "http://example.com/stream.m3u8"
        result = await helper.async_convert_stream(source_url)

        assert result is not None
        # Should use external host, not HA host
        assert "frigate.example.com" in result
        # External go2rtc uses standard port 8554
        assert result.startswith("rtsp://frigate.example.com:8554/")
        assert GO2RTC_STREAM_PREFIX in result

        await helper.async_stop()

    async def test_external_go2rtc_delete_uses_configured_url(
        self,
        mock_hass_with_external_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test that stream deletion uses external go2rtc URL."""
        helper = Go2rtcHelper(mock_hass_with_external_go2rtc)

        # Add then remove a stream
        await helper.async_convert_stream("http://example.com/stream.m3u8")
        await helper._cleanup_all_streams()

        # Verify DELETE was called with external server URL
        call_args = mock_aiohttp_session.delete.call_args
        url = call_args[0][0]
        assert "http://frigate.example.com:1984/api/streams" in url

        await helper.async_stop()

    def test_get_go2rtc_config_external_server(
        self,
        mock_hass_with_external_go2rtc: MagicMock,
    ) -> None:
        """Test _get_go2rtc_config parses external server URL correctly."""
        helper = Go2rtcHelper(mock_hass_with_external_go2rtc)

        api_url, rtsp_host, rtsp_port = helper._get_go2rtc_config()

        assert api_url == "http://frigate.example.com:1984"
        assert rtsp_host == "frigate.example.com"
        # External servers use standard go2rtc RTSP port
        assert rtsp_port == GO2RTC_EXTERNAL_RTSP_PORT

    def test_get_go2rtc_config_localhost(
        self,
        mock_hass_with_go2rtc: MagicMock,
    ) -> None:
        """Test _get_go2rtc_config uses HA-managed ports for localhost."""
        helper = Go2rtcHelper(mock_hass_with_go2rtc)

        api_url, rtsp_host, rtsp_port = helper._get_go2rtc_config()

        assert api_url == "http://127.0.0.1:11984"
        assert rtsp_host == "127.0.0.1"
        # HA-managed uses port 18554
        assert rtsp_port == GO2RTC_DEFAULT_RTSP_PORT

    def test_get_go2rtc_config_fallback_without_go2rtc(
        self,
        mock_hass_without_go2rtc: MagicMock,
    ) -> None:
        """Test _get_go2rtc_config falls back to defaults when go2rtc unavailable."""
        helper = Go2rtcHelper(mock_hass_without_go2rtc)

        api_url, rtsp_host, rtsp_port = helper._get_go2rtc_config()

        assert api_url == GO2RTC_DEFAULT_API_URL
        assert rtsp_host == "127.0.0.1"
        assert rtsp_port == GO2RTC_DEFAULT_RTSP_PORT

    def test_get_go2rtc_config_caches_values(
        self,
        mock_hass_with_external_go2rtc: MagicMock,
    ) -> None:
        """Test _get_go2rtc_config caches values after first call."""
        helper = Go2rtcHelper(mock_hass_with_external_go2rtc)

        # First call
        api_url1, rtsp_host1, rtsp_port1 = helper._get_go2rtc_config()

        # Modify the mock to verify caching works
        mock_hass_with_external_go2rtc.data[GO2RTC_DOMAIN].url = "http://changed.com:9999"

        # Second call should return cached values
        api_url2, rtsp_host2, rtsp_port2 = helper._get_go2rtc_config()

        assert api_url1 == api_url2
        assert rtsp_host1 == rtsp_host2
        assert rtsp_port1 == rtsp_port2

    async def test_external_go2rtc_does_not_use_ha_host_for_rtsp(
        self,
        mock_hass_with_external_go2rtc: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test external go2rtc doesn't try to use HA's internal URL for RTSP."""
        helper = Go2rtcHelper(mock_hass_with_external_go2rtc)

        # Even if get_url returns HA's internal address, RTSP should use external host
        with patch(
            "custom_components.zowietek.go2rtc_helper.get_url",
            return_value="http://192.168.1.100:8123",
        ):
            rtsp_url = await helper.async_convert_stream("http://example.com/stream.m3u8")

            assert rtsp_url is not None
            # Should NOT contain HA's IP
            assert "192.168.1.100" not in rtsp_url
            # Should contain external go2rtc host
            assert "frigate.example.com" in rtsp_url

        await helper.async_stop()
