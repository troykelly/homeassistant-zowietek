"""Helper module for go2rtc stream conversion.

This module provides the Go2rtcHelper class that enables conversion of
incompatible stream formats (HLS, camera entities, etc.) to RTSP via
Home Assistant's built-in go2rtc service.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import aiohttp
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import (
    GO2RTC_DEFAULT_API_URL,
    GO2RTC_DEFAULT_RTSP_PORT,
    GO2RTC_DOMAIN,
    GO2RTC_EXTERNAL_RTSP_PORT,
    GO2RTC_STREAM_PREFIX,
    GO2RTC_STREAM_TTL,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class ManagedStream:
    """A stream managed by the go2rtc helper.

    Attributes:
        name: The unique stream name in go2rtc.
        source_url: The original source URL that was converted.
        rtsp_url: The RTSP URL to access the converted stream.
        last_accessed: Timestamp of last access for TTL cleanup.
    """

    name: str
    source_url: str
    rtsp_url: str
    last_accessed: datetime = field(default_factory=datetime.now)


class Go2rtcHelper:
    """Helper class for go2rtc stream conversion.

    This class manages the lifecycle of streams converted through go2rtc,
    including adding streams, caching for reuse, and TTL-based cleanup.

    Attributes:
        is_available: Whether go2rtc is available in Home Assistant.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the helper.

        Args:
            hass: The Home Assistant instance.
        """
        self._hass = hass
        self._streams: dict[str, ManagedStream] = {}
        self._cleanup_task: asyncio.Task[None] | None = None
        self._session: aiohttp.ClientSession | None = None
        self._api_url: str | None = None
        self._rtsp_host: str | None = None
        self._rtsp_port: int = GO2RTC_DEFAULT_RTSP_PORT

    @property
    def is_available(self) -> bool:
        """Check if go2rtc is available in Home Assistant.

        Returns:
            True if go2rtc integration is loaded, False otherwise.
        """
        return GO2RTC_DOMAIN in self._hass.data

    def _get_go2rtc_config(self) -> tuple[str, str, int]:
        """Get the go2rtc API URL and RTSP host/port from Home Assistant config.

        Reads the go2rtc configuration from hass.data if available.
        Falls back to default localhost values if not configured.

        Returns:
            Tuple of (api_url, rtsp_host, rtsp_port).
        """
        # Check if we have cached values
        if self._api_url is not None and self._rtsp_host is not None:
            _LOGGER.debug("Using cached go2rtc config: %s", self._api_url)
            return self._api_url, self._rtsp_host, self._rtsp_port

        # Try to get the go2rtc config from Home Assistant's data store
        # The go2rtc integration stores a Go2RtcConfig dataclass with url and session
        go2rtc_data = self._hass.data.get(GO2RTC_DOMAIN)

        if go2rtc_data is not None and hasattr(go2rtc_data, "url"):
            # User has configured go2rtc (possibly external server)
            configured_url = go2rtc_data.url
            _LOGGER.debug("Using go2rtc URL from HA config: %s", configured_url)

            # Parse the URL to extract host for RTSP
            parsed = urlparse(configured_url)
            api_url = configured_url.rstrip("/")
            rtsp_host = parsed.hostname or "127.0.0.1"

            # For external go2rtc servers, RTSP port is typically 8554 (standard)
            # For HA-managed go2rtc, RTSP port is 18554
            # We check if this is localhost (HA-managed) or external
            if rtsp_host in ("127.0.0.1", "localhost", "::1"):
                rtsp_port = GO2RTC_DEFAULT_RTSP_PORT  # 18554 for HA-managed
            else:
                # External server - use standard go2rtc RTSP port
                rtsp_port = GO2RTC_EXTERNAL_RTSP_PORT

            self._api_url = api_url
            self._rtsp_host = rtsp_host
            self._rtsp_port = rtsp_port
            return api_url, rtsp_host, rtsp_port

        # Fall back to default HA-managed localhost values
        _LOGGER.debug("Using default go2rtc localhost URL")
        self._api_url = GO2RTC_DEFAULT_API_URL
        self._rtsp_host = "127.0.0.1"
        self._rtsp_port = GO2RTC_DEFAULT_RTSP_PORT
        return self._api_url, self._rtsp_host, self._rtsp_port

    def _get_ha_host(self) -> str:
        """Get the Home Assistant host address for external access.

        This is needed because the ZowieBox needs to connect to go2rtc
        via the network, not localhost.

        Returns:
            The hostname or IP address of the Home Assistant instance.
        """
        try:
            # Try to get the internal URL (preferred for local network devices)
            internal_url = get_url(
                self._hass,
                allow_internal=True,
                allow_external=False,
                allow_cloud=False,
                allow_ip=True,
            )
            parsed = urlparse(internal_url)
            return parsed.hostname or "127.0.0.1"
        except NoURLAvailableError:
            _LOGGER.warning(
                "Could not determine Home Assistant internal URL, "
                "using localhost - this may not work for external devices"
            )
            return "127.0.0.1"

    def _format_host_for_url(self, host: str) -> str:
        """Format a host address for use in a URL.

        IPv6 addresses must be enclosed in brackets for URLs.

        Args:
            host: The hostname or IP address.

        Returns:
            The host formatted for URL use (IPv6 addresses wrapped in brackets).
        """
        # Check if this is an IPv6 address (contains colon but not already bracketed)
        if ":" in host and not host.startswith("["):
            return f"[{host}]"
        return host

    async def async_start(self) -> None:
        """Start the helper and begin the cleanup task.

        This should be called when the integration is set up.
        """
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def async_stop(self) -> None:
        """Stop the helper and cleanup all streams.

        This should be called when the integration is unloaded.
        """
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
        self._cleanup_task = None

        await self._cleanup_all_streams()

        if self._session:
            await self._session.close()
            self._session = None

    async def async_convert_stream(self, source_url: str) -> str | None:
        """Convert a stream URL via go2rtc and return the RTSP URL.

        If the stream has already been converted, returns the cached RTSP URL.

        Args:
            source_url: The source stream URL to convert.

        Returns:
            The RTSP URL for the converted stream, or None if conversion failed.
        """
        if not self.is_available:
            _LOGGER.debug("go2rtc not available, cannot convert stream")
            return None

        # Generate unique stream name from URL hash (12 chars for better uniqueness)
        url_hash = hashlib.md5(source_url.encode()).hexdigest()[:12]
        stream_name = f"{GO2RTC_STREAM_PREFIX}{url_hash}"

        # Check if already converted (cache hit)
        if stream_name in self._streams:
            self._streams[stream_name].last_accessed = datetime.now()
            _LOGGER.debug("Reusing cached stream: %s", stream_name)
            return self._streams[stream_name].rtsp_url

        # Get go2rtc configuration (API URL and RTSP host/port)
        _, rtsp_host, rtsp_port = self._get_go2rtc_config()

        # Add stream to go2rtc
        try:
            await self._add_stream(stream_name, source_url)

            # Determine the RTSP host for the ZowieBox to connect to
            # For external go2rtc servers, use the configured host directly
            # For localhost (HA-managed), use HA's network-accessible address
            if rtsp_host in ("127.0.0.1", "localhost", "::1"):
                # HA-managed go2rtc - use HA's actual host address
                rtsp_connect_host = self._get_ha_host()
            else:
                # External go2rtc server - use the configured host
                rtsp_connect_host = rtsp_host

            # Format host for URL (handles IPv6 addresses)
            formatted_host = self._format_host_for_url(rtsp_connect_host)
            rtsp_url = f"rtsp://{formatted_host}:{rtsp_port}/{stream_name}"

            self._streams[stream_name] = ManagedStream(
                name=stream_name,
                source_url=source_url,
                rtsp_url=rtsp_url,
            )

            _LOGGER.info("Created go2rtc stream: %s -> %s", stream_name, rtsp_url)
            return rtsp_url

        except Exception as err:
            _LOGGER.error("Failed to add stream to go2rtc: %s", err)
            return None

    async def async_convert_camera(self, entity_id: str) -> str | None:
        """Convert a camera entity to RTSP via go2rtc.

        Uses go2rtc's native camera entity support via ffmpeg.

        Args:
            entity_id: The camera entity ID (e.g., "camera.front_door").

        Returns:
            The RTSP URL for the converted camera stream, or None if conversion failed.
        """
        if not self.is_available:
            _LOGGER.debug("go2rtc not available, cannot convert camera")
            return None

        # Verify camera entity exists
        state = self._hass.states.get(entity_id)
        if state is None:
            _LOGGER.error("Camera entity not found: %s", entity_id)
            return None

        # Use go2rtc's ffmpeg source format for Home Assistant cameras
        source_url = f"ffmpeg:{entity_id}"
        return await self.async_convert_stream(source_url)

    async def _add_stream(self, name: str, source: str) -> None:
        """Add a stream to go2rtc via REST API.

        Args:
            name: The stream name to use in go2rtc.
            source: The source URL for the stream.

        Raises:
            RuntimeError: If the go2rtc API returns an error.
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()

        api_url, _, _ = self._get_go2rtc_config()
        url = f"{api_url}/api/streams"

        async with self._session.put(
            url,
            params={"src": source, "name": name},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"go2rtc API error: {resp.status} - {text}")

    async def _delete_stream(self, name: str) -> None:
        """Delete a stream from go2rtc.

        Args:
            name: The stream name to delete.
        """
        if self._session is None:
            return

        api_url, _, _ = self._get_go2rtc_config()
        url = f"{api_url}/api/streams"

        try:
            async with self._session.delete(
                url,
                params={"src": name},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                # 404 is acceptable (stream may not exist)
                if resp.status not in (200, 404):
                    _LOGGER.warning("Failed to delete stream %s: status %s", name, resp.status)
        except Exception as err:
            _LOGGER.warning("Error deleting stream %s: %s", name, err)

    async def _cleanup_loop(self) -> None:
        """Periodically clean up inactive streams.

        Runs every 60 seconds to check for streams that have exceeded the TTL.
        """
        while True:
            await asyncio.sleep(60)
            await self._cleanup_inactive_streams()

    async def _cleanup_inactive_streams(self) -> None:
        """Remove streams that haven't been accessed within the TTL period."""
        now = datetime.now()
        ttl = timedelta(seconds=GO2RTC_STREAM_TTL)

        to_remove = [
            name for name, stream in self._streams.items() if now - stream.last_accessed > ttl
        ]

        for name in to_remove:
            await self._delete_stream(name)
            del self._streams[name]
            _LOGGER.debug("Cleaned up inactive stream: %s", name)

    async def _cleanup_all_streams(self) -> None:
        """Remove all managed streams from go2rtc."""
        for name in list(self._streams.keys()):
            await self._delete_stream(name)
        self._streams.clear()
        _LOGGER.debug("Cleaned up all managed streams")
