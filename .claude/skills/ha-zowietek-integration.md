---
name: ha-zowietek-integration
description: Home Assistant integration patterns for Zowietek
---

# Home Assistant Integration Patterns

## Integration Structure

```
custom_components/zowietek/
├── __init__.py           # Setup and unload
├── manifest.json         # Metadata
├── config_flow.py        # Configuration UI
├── const.py              # Constants
├── coordinator.py        # Data updates
├── entity.py             # Base entity
├── api.py                # API client
├── sensor.py             # Sensor platform
├── switch.py             # Switch platform
├── binary_sensor.py      # Binary sensor platform
├── button.py             # Button platform
├── select.py             # Select platform
├── diagnostics.py        # Debug info
├── strings.json          # Translations
└── translations/en.json
```

## manifest.json

```json
{
  "domain": "zowietek",
  "name": "Zowietek",
  "codeowners": ["@troykelly"],
  "config_flow": true,
  "documentation": "https://github.com/troykelly/homeassistant-zowietek",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/troykelly/homeassistant-zowietek/issues",
  "requirements": ["aiohttp>=3.8.0"],
  "version": "0.1.0"
}
```

## Config Flow

```python
"""Config flow for Zowietek integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

from .api import ZowietekClient
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_USERNAME, default="admin"): str,
    vol.Required(CONF_PASSWORD, default="admin"): str,
})


class ZowietekConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zowietek."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = ZowietekClient(
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )

            try:
                info = await client.get_system_info()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info.get("device_name", "ZowieBox"),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
```

## Coordinator

```python
"""Data coordinator for Zowietek integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZowietekClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZowietekCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Zowietek data update coordinator."""

    def __init__(self, hass: HomeAssistant, client: ZowietekClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from device."""
        try:
            return await self.client.get_all_info()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
```

## Base Entity

```python
"""Base entity for Zowietek integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZowietekCoordinator


class ZowietekEntity(CoordinatorEntity[ZowietekCoordinator]):
    """Base class for Zowietek entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ZowietekCoordinator, device_id: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self.coordinator.data.get("device_name", "ZowieBox"),
            manufacturer="Zowietek",
            model=self.coordinator.data.get("model", "ZowieBox"),
            sw_version=self.coordinator.data.get("firmware_version"),
        )
```

## Sensor Platform

```python
"""Sensor platform for Zowietek integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZowietekCoordinator
from .entity import ZowietekEntity

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="video_resolution",
        name="Video Resolution",
        icon="mdi:video",
    ),
    SensorEntityDescription(
        key="stream_bitrate",
        name="Stream Bitrate",
        native_unit_of_measurement="Mbps",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek sensors."""
    coordinator: ZowietekCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        ZowietekSensor(coordinator, entry.unique_id, description)
        for description in SENSORS
    )


class ZowietekSensor(ZowietekEntity, SensorEntity):
    """Zowietek sensor entity."""

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        device_id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def native_value(self) -> str | int | float | None:
        """Return the sensor value."""
        return self.coordinator.data.get(self.entity_description.key)
```

## Integration Setup

```python
"""The Zowietek integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import ZowietekClient
from .const import DOMAIN
from .coordinator import ZowietekCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zowietek from a config entry."""
    client = ZowietekClient(
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    coordinator = ZowietekCoordinator(hass, client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
```
