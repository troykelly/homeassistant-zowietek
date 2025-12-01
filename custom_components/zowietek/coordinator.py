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

    async def _async_update_data(self) -> ZowietekData:
        """Fetch data from ZowieBox device.

        This method fetches all data types in parallel for better performance.
        It handles authentication errors by raising ConfigEntryAuthFailed,
        and other errors by raising UpdateFailed.

        Returns:
            ZowietekData containing all device information.

        Raises:
            ConfigEntryAuthFailed: If authentication fails.
            UpdateFailed: If the connection fails or API returns an error.
        """
        try:
            # Fetch all data types in parallel for better performance
            (
                device_info,
                video_info,
                input_signal,
                output_info,
                stream_publish,
                ndi_config,
            ) = await asyncio.gather(
                self.client.async_get_device_info(),
                self.client.async_get_video_info(),
                self.client.async_get_input_signal(),
                self.client.async_get_output_info(),
                self.client.async_get_stream_publish_info(),
                self.client.async_get_ndi_config(),
            )

            # Combine video info with input signal and output info
            video_combined = {
                **video_info,
                "input": input_signal,
                "output": output_info,
            }

            # Combine stream info with NDI config
            stream_combined = {
                **stream_publish,
                **ndi_config,
            }

            return ZowietekData(
                system=device_info,
                video=video_combined,
                audio={},  # Audio info not yet implemented in API
                stream=stream_combined,
                network={},  # Network info not yet implemented in API
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
