"""Data update coordinator for Zowietek integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZowietekClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .exceptions import (
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekError,
)
from .models import ZowietekData

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class ZowietekCoordinator(DataUpdateCoordinator[ZowietekData]):
    """Class to manage fetching Zowietek data from the device.

    This coordinator handles polling the ZowieBox device for all data types
    and distributing that data to all entities. It uses parallel API calls
    for better performance and handles errors appropriately.
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
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.config_entry = entry
        self.client = ZowietekClient(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )

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

            # Add output format from output_info
            if output_info:
                video_data["output_format"] = output_info.get("format", "")

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

            return ZowietekData(
                system=system_data,
                video=video_data,
                audio=audio_info if audio_info else {},
                stream=stream_data,
                network={},  # Network info not yet implemented in API
                dashboard=dashboard_data,
            )

        except ZowietekAuthError as err:
            # Authentication errors should trigger reauthentication flow
            raise ConfigEntryAuthFailed(
                f"Authentication failed for {self.config_entry.data[CONF_HOST]}"
            ) from err
        except ZowietekConnectionError as err:
            # Connection errors mark entities as unavailable
            raise UpdateFailed(
                f"Unable to connect to {self.config_entry.data[CONF_HOST]}: {err}"
            ) from err
        except ZowietekError as err:
            # Other API errors also mark entities as unavailable
            raise UpdateFailed(
                f"Error communicating with {self.config_entry.data[CONF_HOST]}: {err}"
            ) from err
