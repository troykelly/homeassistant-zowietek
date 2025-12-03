"""Data update coordinator for Zowietek integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_PASSWORD, CONF_TYPE, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZowietekClient
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_USE_GO2RTC,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_GO2RTC,
    DOMAIN,
)
from .device_trigger import EVENT_TYPE
from .exceptions import (
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekError,
)
from .models import ZowietekData

if TYPE_CHECKING:
    from .go2rtc_helper import Go2rtcHelper

_LOGGER = logging.getLogger(__name__)


class ZowietekCoordinator(DataUpdateCoordinator[ZowietekData]):
    """Class to manage fetching Zowietek data from the device.

    This coordinator handles polling the ZowieBox device for all data types
    and distributing that data to all entities. It uses parallel API calls
    for better performance and handles errors appropriately.

    Connection recovery is handled automatically:
    - Temporary network failures mark entities as unavailable
    - The coordinator continues polling and recovers when the device returns
    - Auth failures trigger the reauthentication flow
    - Consecutive failures are tracked for diagnostics
    """

    config_entry: ConfigEntry[Any]

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry[Any],
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            entry: The config entry for this integration instance.
        """
        # Get scan interval from options, falling back to default
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.config_entry = entry
        self.client = ZowietekClient(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        self._consecutive_failures: int = 0
        # Track previous state for device trigger events
        self._prev_streaming: bool | None = None
        self._prev_video_input: bool | None = None
        # go2rtc integration (initialized by async_setup_entry)
        self.go2rtc_helper: Go2rtcHelper | None = None
        self.go2rtc_enabled: bool = entry.options.get(CONF_USE_GO2RTC, DEFAULT_USE_GO2RTC)

    @property
    def consecutive_failures(self) -> int:
        """Return the number of consecutive update failures.

        This counter is incremented each time an update fails and reset
        to zero on successful updates. Useful for diagnostics and
        determining if a device has persistent connection issues.
        """
        return self._consecutive_failures

    @property
    def device_id(self) -> str:
        """Return the device ID.

        Returns the device serial number from the fetched data,
        falling back to the config entry unique_id if not available.
        """
        if self.data is not None:
            device_sn = self.data.system.get("devicesn")
            if device_sn:
                return str(device_sn)
        # Fallback to config entry unique_id
        return self.config_entry.unique_id or ""

    @property
    def device_name(self) -> str:
        """Return the device name.

        Returns the device name from the fetched data,
        falling back to the config entry title if not available.
        """
        if self.data is not None:
            device_name = self.data.system.get("devicename")
            if device_name:
                return str(device_name)
        # Fallback to config entry title
        return self.config_entry.title

    def _get_ha_device_id(self) -> str | None:
        """Get the Home Assistant device ID for this device.

        Returns:
            The HA device registry ID, or None if not found.
        """
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, str(self.config_entry.unique_id))}
        )
        return device.id if device else None

    def _is_streaming(self, data: ZowietekData) -> bool:
        """Check if any streaming output is enabled.

        Args:
            data: The device data to check.

        Returns:
            True if any stream (NDI, RTMP, or SRT) is enabled.
        """
        stream_data = data.stream

        # Check NDI
        ndi_switch = stream_data.get("ndi_switch")
        if ndi_switch is not None and str(ndi_switch) == "1":
            return True

        # Check RTMP and SRT in publish list
        publish_list = stream_data.get("publish")
        if isinstance(publish_list, list):
            for entry in publish_list:
                if isinstance(entry, dict):
                    switch = entry.get("switch")
                    if switch is not None and str(switch) == "1":
                        return True

        return False

    def _has_video_input(self, data: ZowietekData) -> bool:
        """Check if video input signal is detected.

        Args:
            data: The device data to check.

        Returns:
            True if video input signal is detected.
        """
        video_data = data.video

        # Try 'input_signal' first, then fall back to 'input_hdmi_signal'
        signal = video_data.get("input_signal")
        if signal is None:
            signal = video_data.get("input_hdmi_signal")

        if signal is None:
            return False

        return str(signal) == "1"

    def _fire_trigger_event(self, trigger_type: str) -> None:
        """Fire a device trigger event.

        Args:
            trigger_type: The trigger type to fire (e.g., 'stream_started').
        """
        device_id = self._get_ha_device_id()
        if device_id is None:
            _LOGGER.debug(
                "Cannot fire trigger event %s: device not found in registry",
                trigger_type,
            )
            return

        _LOGGER.debug(
            "Firing device trigger event: %s for device %s",
            trigger_type,
            device_id,
        )
        self.hass.bus.async_fire(
            EVENT_TYPE,
            {
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: trigger_type,
            },
        )

    def _check_and_fire_triggers(self, new_data: ZowietekData) -> None:
        """Check for state changes and fire appropriate trigger events.

        Args:
            new_data: The newly fetched device data.
        """
        current_streaming = self._is_streaming(new_data)
        current_video_input = self._has_video_input(new_data)

        # Check streaming state change
        if self._prev_streaming is not None:
            if current_streaming and not self._prev_streaming:
                self._fire_trigger_event("stream_started")
            elif not current_streaming and self._prev_streaming:
                self._fire_trigger_event("stream_stopped")

        # Check video input state change
        if self._prev_video_input is not None:
            if current_video_input and not self._prev_video_input:
                self._fire_trigger_event("video_input_detected")
            elif not current_video_input and self._prev_video_input:
                self._fire_trigger_event("video_input_lost")

        # Update previous state
        self._prev_streaming = current_streaming
        self._prev_video_input = current_video_input

    async def _async_fetch_optional(
        self,
        name: str,
        coro: object,
    ) -> dict[str, str | int]:
        """Fetch optional data that may not be available on all devices.

        Some API endpoints are not supported by all firmware versions.
        This method handles failures gracefully by returning an empty dict.

        Args:
            name: Name of the endpoint for logging.
            coro: The coroutine to execute.

        Returns:
            The API response data, or empty dict if the endpoint fails.
        """
        try:
            result = await coro  # type: ignore[misc]
            if isinstance(result, dict):
                return result
            return {}
        except ZowietekAuthError:
            # Re-raise auth errors - these should not be ignored
            raise
        except ZowietekError as err:
            # Log but don't fail - endpoint may not be supported
            _LOGGER.debug(
                "Optional endpoint %s not available: %s",
                name,
                err,
            )
            return {}

    @staticmethod
    def _get_main_encoder(
        venc_info: dict[str, str | int],
    ) -> dict[str, str | int | dict[str, str | int | list[str]]] | None:
        """Get the main encoder channel from venc info.

        The API returns a list of encoder channels. The main channel
        is typically index 0 with desc="main".

        Args:
            venc_info: The venc response from the API.

        Returns:
            The main encoder channel dict, or None if not found.
        """
        venc_list = venc_info.get("venc")
        if not isinstance(venc_list, list) or not venc_list:
            return None

        # Look for main channel first
        for venc in venc_list:
            if isinstance(venc, dict) and venc.get("desc") == "main":
                return venc

        # Fallback to first channel
        first = venc_list[0]
        if isinstance(first, dict):
            return first
        return None

    async def _async_update_data(self) -> ZowietekData:
        """Fetch data from ZowieBox device.

        This method fetches data types in parallel for better performance.
        Required endpoints (video info, input/output) will cause UpdateFailed
        if they fail. Optional endpoints (device info, NDI) will gracefully
        degrade to empty data.

        Returns:
            ZowietekData containing all device information.

        Raises:
            ConfigEntryAuthFailed: If authentication fails.
            UpdateFailed: If required endpoints fail.
        """
        import time

        start = time.monotonic()
        try:
            # Fetch all data in parallel for better performance
            (
                input_signal,
                output_info,
                venc_info,
                stream_publish,
                ndi_config,
                audio_info,
                sys_attr,
                dashboard_info,
                streamplay_info,
                decoder_status,
                ndi_sources,
                run_status,
            ) = await asyncio.gather(
                self.client.async_get_input_signal(),
                self.client.async_get_output_info(),
                self.client.async_get_venc_info(),
                self.client.async_get_stream_publish_info(),
                self._async_fetch_optional(
                    "ndi_config",
                    self.client.async_get_ndi_config(),
                ),
                self._async_fetch_optional(
                    "audio_info",
                    self.client.async_get_audio_info(),
                ),
                self._async_fetch_optional(
                    "sys_attr",
                    self.client.async_get_sys_attr_info(),
                ),
                self._async_fetch_optional(
                    "dashboard_info",
                    self.client.async_get_dashboard_info(),
                ),
                self._async_fetch_optional(
                    "streamplay_info",
                    self.client.async_get_streamplay_info(),
                ),
                self._async_fetch_optional(
                    "decoder_status",
                    self.client.async_get_decoder_status(),
                ),
                self._async_fetch_optional(
                    "ndi_sources",
                    self.client.async_get_ndi_sources(),
                ),
                self._async_fetch_optional(
                    "run_status",
                    self.client.async_get_run_status(),
                ),
            )

            # Extract main encoder channel (channel 0, desc="main")
            main_encoder = self._get_main_encoder(venc_info)

            # Build flattened video data for sensors
            video_data: dict[str, str | int] = {}

            # Add flattened encoder values for easy sensor access
            if main_encoder:
                codec_info = main_encoder.get("codec")
                codec_list: list[str] = []
                codec_id = 0
                if isinstance(codec_info, dict):
                    codec_list_raw = codec_info.get("codec_list", [])
                    if isinstance(codec_list_raw, list):
                        codec_list = [str(c) for c in codec_list_raw]
                    selected_id = codec_info.get("selected_id", 0)
                    if isinstance(selected_id, int):
                        codec_id = selected_id
                codec_name = codec_list[codec_id] if codec_id < len(codec_list) else ""

                width = main_encoder.get("width", 0)
                height = main_encoder.get("height", 0)
                video_data["enc_resolution"] = f"{width}x{height}"
                framerate = main_encoder.get("framerate", 0)
                if isinstance(framerate, int):
                    video_data["enc_framerate"] = framerate
                bitrate = main_encoder.get("bitrate", 0)
                if isinstance(bitrate, int):
                    video_data["enc_bitrate"] = bitrate
                video_data["enc_type"] = codec_name
                # Store codec list and selected_id for select entity
                video_data["codec_list"] = codec_list  # type: ignore[assignment]
                video_data["codec_selected_id"] = codec_id

            # Add output format from output_info
            if output_info:
                video_data["output_format"] = output_info.get("format", "")
                # Store output format list for select entity
                format_list_info = output_info.get("format_list")
                if isinstance(format_list_info, dict):
                    fmt_list_raw = format_list_info.get("list", [])
                    if isinstance(fmt_list_raw, list):
                        video_data["output_format_list"] = [  # type: ignore[assignment]
                            str(f) for f in fmt_list_raw
                        ]
                    fmt_selected_id = format_list_info.get("selected_id", 0)
                    if isinstance(fmt_selected_id, int):
                        video_data["output_format_selected_id"] = fmt_selected_id

            # Add input signal data for binary sensor video_input detection
            # Flatten input_signal into video_data with "input_" prefix
            if input_signal and isinstance(input_signal, dict):
                # Support both 'signal' and 'hdmi_signal' keys for compatibility
                signal = input_signal.get("signal")
                if signal is not None and isinstance(signal, (int, str)):
                    video_data["input_signal"] = (
                        signal
                        if isinstance(signal, int)
                        else int(signal)
                        if signal.isdigit()
                        else 0
                    )
                hdmi_signal = input_signal.get("hdmi_signal")
                if hdmi_signal is not None and isinstance(hdmi_signal, (int, str)):
                    video_data["input_hdmi_signal"] = (
                        hdmi_signal
                        if isinstance(hdmi_signal, int)
                        else int(hdmi_signal)
                        if str(hdmi_signal).isdigit()
                        else 0
                    )

            # Build stream data with NDI info
            stream_data: dict[str, str | int | list[dict[str, str | int]]] = {
                **stream_publish,
            }

            # Add NDI config fields
            if ndi_config:
                stream_data["ndi_switch"] = ndi_config.get("switch", 0)
                stream_data["ndi_name"] = ndi_config.get("machinename", "")
                stream_data["ndi_mode_id"] = ndi_config.get("mode_id", 0)
                stream_data["ndi_groups"] = ndi_config.get("groups", "")
                stream_data["ndi_activated"] = ndi_config.get("activate", 0)

            # Build system data from sys_attr (preferred) or fall back to NDI config
            system_data: dict[str, str | int] = {}
            if sys_attr:
                # Use sys_attr for comprehensive device info
                system_data["devicesn"] = sys_attr.get("SN", "")
                system_data["devicename"] = sys_attr.get("device_name", "")
                system_data["firmware_version"] = sys_attr.get("firmware_version", "")
                system_data["hardware_version"] = sys_attr.get("hardware_version", "")
                system_data["model"] = sys_attr.get("model", "ZowieBox")
                system_data["manufacturer"] = sys_attr.get("manufacturer", "Zowietek")
                system_data["ndi_version"] = sys_attr.get("ndi_version", "")
            elif ndi_config:
                # Fall back to NDI machine name as device identifier
                system_data["devicename"] = ndi_config.get("machinename", "")
                # Extract serial from machine name if present (format: ZowieBox-XXXXX)
                machine_name = ndi_config.get("machinename", "")
                if "-" in machine_name:
                    system_data["devicesn"] = machine_name.split("-")[-1]
                system_data["model"] = "ZowieBox"
                system_data["manufacturer"] = "Zowietek"

            elapsed = time.monotonic() - start

            # Log recovery if we were previously failing
            if self._consecutive_failures > 0:
                _LOGGER.info(
                    "Connection to %s restored after %d failed attempts",
                    self.config_entry.data[CONF_HOST],
                    self._consecutive_failures,
                )
                self._consecutive_failures = 0
            else:
                _LOGGER.debug(
                    "Finished fetching zowietek data in %.3f seconds (success: True)",
                    elapsed,
                )

            # Build dashboard data
            dashboard_data: dict[str, str | int | float] = {}
            if dashboard_info:
                dashboard_data["uptime"] = dashboard_info.get("persistent_time", "")
                dashboard_data["start_time"] = dashboard_info.get("device_strat_time", "")
                dashboard_data["cpu_temp"] = dashboard_info.get("cpu_temp", 0.0)
                dashboard_data["cpu_usage"] = dashboard_info.get("cpu_payload", 0.0)
                memory = dashboard_info.get("memory_info", {})
                if isinstance(memory, dict):
                    dashboard_data["memory_used"] = memory.get("used", 0)
                    dashboard_data["memory_total"] = memory.get("total", 0)

            # Build streamplay data for media player
            streamplay_data: dict[str, str | int | list[dict[str, str | int]]] = {}
            if streamplay_info:
                streamplay_list = streamplay_info.get("streamplay", [])
                if isinstance(streamplay_list, list):
                    streamplay_data["sources"] = streamplay_list
                else:
                    streamplay_data["sources"] = []
            else:
                streamplay_data["sources"] = []

            # Build decoder status data
            decoder_status_data: dict[str, str | int] = {}
            if decoder_status:
                decoder_status_data["state"] = decoder_status.get("decoder_state", 0)
                decoder_status_data["active_source"] = decoder_status.get("active_source", "")
                decoder_status_data["active_index"] = decoder_status.get("active_index", -1)
                decoder_status_data["width"] = decoder_status.get("width", 0)
                decoder_status_data["height"] = decoder_status.get("height", 0)
                decoder_status_data["framerate"] = decoder_status.get("framerate", 0)
                decoder_status_data["bandwidth"] = decoder_status.get("bandwidth", 0)

            # Build NDI sources list for media player source selection
            ndi_sources_list: list[dict[str, str | int]] = []
            if ndi_sources:
                sources = ndi_sources.get("ndi_sources", [])
                if isinstance(sources, list):
                    ndi_sources_list = sources

            # Build run status data (power state: running vs standby)
            run_status_data: dict[str, int] = {}
            if run_status:
                # run_status: 0 = standby, 1 = running
                run_status_data["status"] = run_status.get("run_status", 1)
            else:
                # Default to running if status unavailable
                run_status_data["status"] = 1

            result = ZowietekData(
                system=system_data,
                video=video_data,
                audio=audio_info if audio_info else {},
                stream=stream_data,
                network={},  # Network info not yet implemented in API
                dashboard=dashboard_data,
                streamplay=streamplay_data,
                decoder_status=decoder_status_data,
                ndi_sources=ndi_sources_list,
                run_status=run_status_data,
            )

            # Check for state changes and fire device trigger events
            self._check_and_fire_triggers(result)

            return result

        except ZowietekAuthError as err:
            # Authentication errors should trigger reauthentication flow
            self._consecutive_failures += 1
            raise ConfigEntryAuthFailed(
                f"Authentication failed for {self.config_entry.data[CONF_HOST]}"
            ) from err
        except ZowietekConnectionError as err:
            # Connection errors mark entities as unavailable
            self._consecutive_failures += 1
            if self._consecutive_failures == 1:
                _LOGGER.warning(
                    "Connection to %s failed: %s. Entities will be unavailable until "
                    "connection is restored",
                    self.config_entry.data[CONF_HOST],
                    err,
                )
            else:
                _LOGGER.debug(
                    "Connection to %s still unavailable (failure %d): %s",
                    self.config_entry.data[CONF_HOST],
                    self._consecutive_failures,
                    err,
                )
            raise UpdateFailed(
                f"Unable to connect to {self.config_entry.data[CONF_HOST]}: {err}"
            ) from err
        except ZowietekError as err:
            # Other API errors also mark entities as unavailable
            self._consecutive_failures += 1
            if self._consecutive_failures == 1:
                _LOGGER.warning(
                    "Error communicating with %s: %s. Entities will be unavailable "
                    "until connection is restored",
                    self.config_entry.data[CONF_HOST],
                    err,
                )
            else:
                _LOGGER.debug(
                    "Communication with %s still failing (failure %d): %s",
                    self.config_entry.data[CONF_HOST],
                    self._consecutive_failures,
                    err,
                )
            raise UpdateFailed(
                f"Error communicating with {self.config_entry.data[CONF_HOST]}: {err}"
            ) from err
