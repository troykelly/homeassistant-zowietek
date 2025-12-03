"""Media player platform for Zowietek integration.

This module provides a media player entity for ZowieBox devices in decoder mode.
It allows selecting and playing stream sources, including RTSP, RTMP, SRT, and NDI.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.exceptions import HomeAssistantError

from . import ZowietekConfigEntry
from .coordinator import ZowietekCoordinator
from .entity import ZowietekEntity
from .exceptions import ZowietekApiError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

# Prefix for NDI sources in the source list
NDI_SOURCE_PREFIX = "NDI: "

# Name for the Home Assistant managed source (used for play_media)
HA_SOURCE_NAME = "Home Assistant"

# Stream protocols that ZowieBox can handle natively (no conversion needed)
NATIVE_PROTOCOLS = ("rtsp://", "rtmp://", "srt://")

# Streaming manifest extensions that need go2rtc conversion
STREAMING_MANIFEST_EXTENSIONS = (".m3u8", ".mpd")


class ZowietekMediaPlayer(ZowietekEntity, MediaPlayerEntity):
    """Media player entity for ZowieBox decoder functionality.

    Represents the ZowieBox device in decoder mode, allowing users to select
    and play various stream sources including RTSP, RTMP, SRT, and NDI streams.
    Also supports putting the device into standby mode to allow connected
    displays (especially projectors) to power down.
    """

    _attr_icon = "mdi:video-input-antenna"
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: ZowietekCoordinator) -> None:
        """Initialize the media player.

        Args:
            coordinator: The data update coordinator for this device.
        """
        super().__init__(coordinator, "decoder")
        self._attr_translation_key = "decoder"

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the current state of the media player.

        Returns:
            MediaPlayerState.STANDBY if device is in standby mode,
            MediaPlayerState.PLAYING if decoder is active,
            MediaPlayerState.IDLE if stopped,
            None if no data available.
        """
        if self.coordinator.data is None:
            return None

        # Check if device is in standby mode first
        run_status = self.coordinator.data.run_status
        # run_status: 0 = standby, 1 = running
        if run_status.get("status", 1) == 0:
            return MediaPlayerState.STANDBY

        decoder_status = self.coordinator.data.decoder_status
        # Coordinator stores decoder state under 'state' key
        decoder_state = decoder_status.get("state", 0)

        # decoder_state: 1 = playing, 0 = idle/stopped
        if str(decoder_state) == "1":
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def source_list(self) -> list[str]:
        """Return the list of available sources.

        Combines configured streamplay sources with discovered NDI sources.

        Returns:
            List of source names.
        """
        if self.coordinator.data is None:
            return []

        sources: list[str] = []

        # Add configured streamplay sources
        # Coordinator stores streamplay list under 'sources' key
        streamplay_data = self.coordinator.data.streamplay
        streamplay_list = streamplay_data.get("sources", [])
        if isinstance(streamplay_list, list):
            for entry in streamplay_list:
                if isinstance(entry, dict):
                    name = entry.get("name")
                    if name:
                        sources.append(str(name))

        # Add discovered NDI sources with prefix
        ndi_sources = self.coordinator.data.ndi_sources
        if isinstance(ndi_sources, list):
            for entry in ndi_sources:
                if isinstance(entry, dict):
                    name = entry.get("name")
                    if name:
                        sources.append(f"{NDI_SOURCE_PREFIX}{name}")

        return sources

    @property
    def source(self) -> str | None:
        """Return the currently selected source.

        Returns:
            The name of the active source, or None if not playing.
        """
        if self.coordinator.data is None:
            return None

        decoder_status = self.coordinator.data.decoder_status
        # Coordinator stores decoder state under 'state' key
        decoder_state = decoder_status.get("state", 0)

        if str(decoder_state) != "1":
            return None

        active_source = decoder_status.get("active_source")
        if active_source:
            return str(active_source)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes.

        Returns:
            Dictionary containing video resolution, framerate, and bandwidth.
        """
        if self.coordinator.data is None:
            return None

        decoder_status = self.coordinator.data.decoder_status
        width = decoder_status.get("width", 0)
        height = decoder_status.get("height", 0)
        framerate = decoder_status.get("framerate", 0)
        bandwidth = decoder_status.get("bandwidth", 0)

        attrs: dict[str, Any] = {}

        if width and height:
            attrs["video_resolution"] = f"{width}x{height}"
        if framerate:
            attrs["framerate"] = framerate
        if bandwidth:
            attrs["bandwidth_kbps"] = bandwidth

        return attrs if attrs else None

    def _find_source_index(self, source_name: str) -> int | None:
        """Find the index of a source by name.

        Args:
            source_name: The name of the source to find.

        Returns:
            The index of the source, or None if not found.
        """
        if self.coordinator.data is None:
            return None

        # Coordinator stores streamplay list under 'sources' key
        streamplay_data = self.coordinator.data.streamplay
        streamplay_list = streamplay_data.get("sources", [])
        if not isinstance(streamplay_list, list):
            return None

        for entry in streamplay_list:
            if isinstance(entry, dict) and entry.get("name") == source_name:
                index = entry.get("index")
                if index is not None:
                    return int(index)
        return None

    async def async_select_source(self, source: str) -> None:
        """Select a playback source.

        Args:
            source: The name of the source to select.

        Raises:
            HomeAssistantError: If the source cannot be selected.
        """
        try:
            # Check if it's an NDI source
            if source.startswith(NDI_SOURCE_PREFIX):
                ndi_name = source[len(NDI_SOURCE_PREFIX) :]
                await self.coordinator.client.async_enable_ndi_decoding(ndi_name)
            else:
                # Find the source index
                source_index = self._find_source_index(source)
                if source_index is not None:
                    await self.coordinator.client.async_select_streamplay_source(source_index)
                else:
                    raise HomeAssistantError(f"Source not found: {source}")
        except ZowietekApiError as err:
            _LOGGER.error("Failed to select source %s: %s", source, err)
            raise HomeAssistantError(f"Failed to select source: {err}") from err

        await self.coordinator.async_request_refresh()

    async def async_media_stop(self) -> None:
        """Stop playback.

        Raises:
            HomeAssistantError: If playback cannot be stopped.
        """
        try:
            await self.coordinator.client.async_stop_streamplay()
        except ZowietekApiError as err:
            _LOGGER.error("Failed to stop playback: %s", err)
            raise HomeAssistantError(f"Failed to stop playback: {err}") from err

        await self.coordinator.async_request_refresh()

    async def async_media_play(self) -> None:
        """Start playback.

        If idle, selects the first available source to start playback.

        Raises:
            HomeAssistantError: If playback cannot be started.
        """
        if self.coordinator.data is None:
            return

        # Find the first enabled source and play it
        # Coordinator stores streamplay list under 'sources' key
        streamplay_data = self.coordinator.data.streamplay
        streamplay_list = streamplay_data.get("sources", [])
        if not isinstance(streamplay_list, list) or not streamplay_list:
            _LOGGER.warning("No sources available to play")
            return

        # Find the first source (prefer enabled ones)
        first_index: int | None = None
        for entry in streamplay_list:
            if isinstance(entry, dict):
                index = entry.get("index")
                if index is not None:
                    first_index = int(index)
                    break

        if first_index is not None:
            try:
                await self.coordinator.client.async_select_streamplay_source(first_index)
            except ZowietekApiError as err:
                _LOGGER.error("Failed to start playback: %s", err)
                raise HomeAssistantError(f"Failed to start playback: {err}") from err

            await self.coordinator.async_request_refresh()

    def _find_ha_source_index(self) -> int | None:
        """Find the index of the Home Assistant managed source.

        Returns:
            The index of the HA source, or None if not found.
        """
        if self.coordinator.data is None:
            return None

        streamplay_data = self.coordinator.data.streamplay
        streamplay_list = streamplay_data.get("sources", [])
        if not isinstance(streamplay_list, list):
            return None

        for entry in streamplay_list:
            if isinstance(entry, dict) and entry.get("name") == HA_SOURCE_NAME:
                index = entry.get("index")
                if index is not None:
                    return int(index)
        return None

    def _find_source_by_url(self, url: str) -> int | None:
        """Find the index of a source by its URL.

        Args:
            url: The URL to search for.

        Returns:
            The index of the source with matching URL, or None if not found.
        """
        if self.coordinator.data is None:
            return None

        streamplay_data = self.coordinator.data.streamplay
        streamplay_list = streamplay_data.get("sources", [])
        if not isinstance(streamplay_list, list):
            return None

        for entry in streamplay_list:
            if isinstance(entry, dict) and entry.get("url") == url:
                index = entry.get("index")
                if index is not None:
                    return int(index)
        return None

    def _needs_go2rtc_conversion(self, url: str) -> bool:
        """Determine if a URL needs conversion via go2rtc.

        Args:
            url: The media URL to check.

        Returns:
            True if the URL needs go2rtc conversion, False if ZowieBox can handle it natively.
        """
        url_lower = url.lower()

        # Camera entity reference - always needs conversion
        if url.startswith("camera."):
            return True

        # Already compatible protocols - no conversion needed
        if any(url_lower.startswith(proto) for proto in NATIVE_PROTOCOLS):
            return False

        # HTTP/HTTPS URLs need evaluation
        if url_lower.startswith(("http://", "https://")):
            # HLS/DASH manifests need conversion
            if any(url_lower.endswith(ext) for ext in STREAMING_MANIFEST_EXTENSIONS):
                return True
            # Plain HTTP streams - ZowieBox can handle directly
            return False

        # Unknown protocol - try conversion if go2rtc available
        return True

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Play a media URL or camera entity.

        First checks if the URL already exists as a configured source and switches
        to it if found. Otherwise, uses a dedicated "Home Assistant" source that
        gets created once and reused for subsequent play_media calls to avoid
        accumulating sources.

        For camera entities and HLS/DASH streams, uses go2rtc to convert the stream
        to RTSP if available and enabled.

        Args:
            media_type: The type of media (e.g., "url", "camera").
            media_id: The URL or camera entity ID to play.
            kwargs: Additional arguments (extra.title is ignored, we use HA_SOURCE_NAME).

        Raises:
            HomeAssistantError: If the media cannot be played.
        """
        url_to_play = media_id

        # Handle camera entity type or camera.* media_id
        is_camera = media_type == "camera" or media_id.startswith("camera.")

        if is_camera:
            # Camera entities always require go2rtc conversion
            entity_id = media_id
            go2rtc_helper = getattr(self.coordinator, "go2rtc_helper", None)
            go2rtc_enabled = getattr(self.coordinator, "go2rtc_enabled", False)

            if not go2rtc_enabled or go2rtc_helper is None:
                raise HomeAssistantError(
                    f"go2rtc is required to play camera entities. "
                    f"Please ensure go2rtc is available and enabled. "
                    f"Camera: {entity_id}"
                )

            converted_url = await go2rtc_helper.async_convert_camera(entity_id)
            if converted_url is None:
                raise HomeAssistantError(f"Failed to convert camera entity via go2rtc: {entity_id}")
            url_to_play = converted_url

        elif self._needs_go2rtc_conversion(media_id):
            # URL needs conversion (HLS, DASH, etc.)
            go2rtc_helper = getattr(self.coordinator, "go2rtc_helper", None)
            go2rtc_enabled = getattr(self.coordinator, "go2rtc_enabled", False)

            if go2rtc_enabled and go2rtc_helper is not None:
                converted_url = await go2rtc_helper.async_convert_stream(media_id)
                if converted_url is not None:
                    url_to_play = converted_url
                    _LOGGER.debug("Converted stream via go2rtc: %s -> %s", media_id, url_to_play)
                else:
                    _LOGGER.warning(
                        "go2rtc conversion failed for %s, attempting direct play",
                        media_id,
                    )
            else:
                _LOGGER.debug(
                    "go2rtc not available/enabled, attempting direct play for %s",
                    media_id,
                )

        try:
            # First, check if this URL already exists as a configured source
            existing_source_index = self._find_source_by_url(url_to_play)
            if existing_source_index is not None:
                # Just switch to the existing source
                await self.coordinator.client.async_select_streamplay_source(existing_source_index)
                await self.coordinator.async_request_refresh()
                return

            # Determine stream type from URL
            streamtype = 1  # Default to RTSP
            url_lower = url_to_play.lower()
            if url_lower.startswith("rtmp://"):
                streamtype = 2
            elif url_lower.startswith("srt://"):
                streamtype = 3
            elif url_lower.startswith("http://") or url_lower.startswith("https://"):
                streamtype = 4

            # Check if we already have a "Home Assistant" source
            ha_source_index = self._find_ha_source_index()

            if ha_source_index is not None:
                # Update existing source with new URL and activate it
                await self.coordinator.client.async_modify_decoding_url(
                    index=ha_source_index,
                    name=HA_SOURCE_NAME,
                    url=url_to_play,
                    streamtype=streamtype,
                    switch=True,
                )
            else:
                # Create new "Home Assistant" source
                await self.coordinator.client.async_add_decoding_url(
                    name=HA_SOURCE_NAME,
                    url=url_to_play,
                    streamtype=streamtype,
                    switch=True,
                )
        except ZowietekApiError as err:
            _LOGGER.error("Failed to play media %s: %s", url_to_play, err)
            raise HomeAssistantError(f"Failed to play media: {err}") from err

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Put the device into standby mode.

        This allows connected displays (especially projectors) to power down
        their lamps and save energy when not in use.

        Raises:
            HomeAssistantError: If the device cannot be put into standby.
        """
        try:
            await self.coordinator.client.async_power_off()
        except ZowietekApiError as err:
            _LOGGER.error("Failed to put device into standby: %s", err)
            raise HomeAssistantError(f"Failed to put device into standby: {err}") from err

        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Wake the device from standby mode.

        Resumes normal operation and re-enables HDMI output.

        Raises:
            HomeAssistantError: If the device cannot be woken.
        """
        try:
            await self.coordinator.client.async_power_on()
        except ZowietekApiError as err:
            _LOGGER.error("Failed to wake device: %s", err)
            raise HomeAssistantError(f"Failed to wake device: {err}") from err

        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek media player entity.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for this integration instance.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    async_add_entities([ZowietekMediaPlayer(coordinator)])
