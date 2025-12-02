"""Custom services for the Zowietek integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .exceptions import ZowietekError

if TYPE_CHECKING:
    from .coordinator import ZowietekCoordinator

_LOGGER = logging.getLogger(__name__)

# Service names
SERVICE_SET_NDI_SETTINGS = "set_ndi_settings"
SERVICE_SET_RTMP_URL = "set_rtmp_url"
SERVICE_SET_SRT_SETTINGS = "set_srt_settings"

# Attribute names
ATTR_DEVICE_ID = "device_id"
ATTR_NAME = "name"
ATTR_GROUP = "group"
ATTR_URL = "url"
ATTR_KEY = "key"
ATTR_PORT = "port"
ATTR_LATENCY = "latency"
ATTR_PASSPHRASE = "passphrase"

# Service schemas
SERVICE_SET_NDI_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_GROUP): cv.string,
    }
)

SERVICE_SET_RTMP_URL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_URL): cv.string,
        vol.Optional(ATTR_KEY): cv.string,
    }
)

SERVICE_SET_SRT_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(ATTR_LATENCY): vol.All(vol.Coerce(int), vol.Range(min=20, max=8000)),
        vol.Optional(ATTR_PASSPHRASE): cv.string,
    }
)


def _get_coordinator_for_device(
    hass: HomeAssistant,
    device_id: str,
) -> ZowietekCoordinator:
    """Get the coordinator for a device by device ID.

    Args:
        hass: Home Assistant instance.
        device_id: The device ID from the device registry.

    Returns:
        The coordinator for the device.

    Raises:
        ServiceValidationError: If the device is not found or not a Zowietek device.
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if device is None:
        raise ServiceValidationError(
            f"Device '{device_id}' not found",
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={"device_id": device_id},
        )

    # Find the config entry for this device
    config_entry_id: str | None = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            # Get the config entry that owns this device
            for entry_id in device.config_entries:
                entry = hass.config_entries.async_get_entry(entry_id)
                if entry and entry.domain == DOMAIN:
                    config_entry_id = entry_id
                    break
            break

    if config_entry_id is None:  # pragma: no cover
        # Defensive check: device exists but no Zowietek identifier found
        raise ServiceValidationError(
            f"Device '{device_id}' is not a Zowietek device",
            translation_domain=DOMAIN,
            translation_key="not_zowietek_device",
            translation_placeholders={"device_id": device_id},
        )

    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None or not hasattr(entry, "runtime_data"):  # pragma: no cover
        # Defensive check: config entry removed or corrupted after device lookup
        raise ServiceValidationError(
            f"Config entry for device '{device_id}' not found",
            translation_domain=DOMAIN,
            translation_key="config_entry_not_found",
            translation_placeholders={"device_id": device_id},
        )

    coordinator: ZowietekCoordinator = entry.runtime_data
    return coordinator


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Zowietek services.

    Args:
        hass: Home Assistant instance.
    """

    async def handle_set_ndi_settings(call: ServiceCall) -> None:
        """Handle the set_ndi_settings service call.

        Sets the NDI name and optionally the group for a ZowieBox device.

        Args:
            call: The service call with device_id, name, and optional group.
        """
        device_id: str = call.data[ATTR_DEVICE_ID]
        name: str = call.data[ATTR_NAME]
        group: str | None = call.data.get(ATTR_GROUP)

        coordinator = _get_coordinator_for_device(hass, device_id)

        try:
            await coordinator.client.async_set_ndi_settings(name=name, group=group)
            await coordinator.async_request_refresh()
        except ZowietekError as err:
            raise HomeAssistantError(
                f"Failed to set NDI settings: {err}",
                translation_domain=DOMAIN,
                translation_key="ndi_settings_failed",
            ) from err

    async def handle_set_rtmp_url(call: ServiceCall) -> None:
        """Handle the set_rtmp_url service call.

        Sets the RTMP URL and optionally the stream key for a ZowieBox device.

        Args:
            call: The service call with device_id, url, and optional key.
        """
        device_id: str = call.data[ATTR_DEVICE_ID]
        url: str = call.data[ATTR_URL]
        key: str | None = call.data.get(ATTR_KEY)

        coordinator = _get_coordinator_for_device(hass, device_id)

        try:
            await coordinator.client.async_set_rtmp_url(url=url, key=key)
            await coordinator.async_request_refresh()
        except ZowietekError as err:
            raise HomeAssistantError(
                f"Failed to set RTMP URL: {err}",
                translation_domain=DOMAIN,
                translation_key="rtmp_url_failed",
            ) from err

    async def handle_set_srt_settings(call: ServiceCall) -> None:
        """Handle the set_srt_settings service call.

        Sets SRT streaming settings including port, latency, and passphrase.

        Args:
            call: The service call with device_id, port, and optional latency/passphrase.
        """
        device_id: str = call.data[ATTR_DEVICE_ID]
        port: int = call.data[ATTR_PORT]
        latency: int | None = call.data.get(ATTR_LATENCY)
        passphrase: str | None = call.data.get(ATTR_PASSPHRASE)

        coordinator = _get_coordinator_for_device(hass, device_id)

        try:
            await coordinator.client.async_set_srt_settings(
                port=port,
                latency=latency,
                passphrase=passphrase,
            )
            await coordinator.async_request_refresh()
        except ZowietekError as err:
            raise HomeAssistantError(
                f"Failed to set SRT settings: {err}",
                translation_domain=DOMAIN,
                translation_key="srt_settings_failed",
            ) from err

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_NDI_SETTINGS,
        handle_set_ndi_settings,
        schema=SERVICE_SET_NDI_SETTINGS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RTMP_URL,
        handle_set_rtmp_url,
        schema=SERVICE_SET_RTMP_URL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SRT_SETTINGS,
        handle_set_srt_settings,
        schema=SERVICE_SET_SRT_SETTINGS_SCHEMA,
    )

    _LOGGER.debug("Registered Zowietek services")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Zowietek services.

    Args:
        hass: Home Assistant instance.
    """
    hass.services.async_remove(DOMAIN, SERVICE_SET_NDI_SETTINGS)
    hass.services.async_remove(DOMAIN, SERVICE_SET_RTMP_URL)
    hass.services.async_remove(DOMAIN, SERVICE_SET_SRT_SETTINGS)

    _LOGGER.debug("Unregistered Zowietek services")
