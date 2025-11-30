---
name: ha-zowietek-integration
description: Use when implementing Home Assistant integration code - covers Nov 2025 best practices for config flows, coordinators, entities, async patterns, manifest, translations, and project structure. Required reading before writing any HA code.
---

# Home Assistant Zowietek Integration Best Practices

## Overview

**Follow Home Assistant 2025 integration patterns exactly.**

This covers config flows, data coordinators, entity patterns, and project structure per current Home Assistant core standards.

## Project Structure

```
custom_components/zowietek/
├── __init__.py           # Integration setup
├── manifest.json         # Integration metadata
├── config_flow.py        # UI configuration flow
├── const.py              # Constants and types
├── coordinator.py        # Data update coordinator
├── entity.py             # Base entity class
├── api.py                # ZowieBox API client wrapper
├── models.py             # Dataclasses for internal models
├── exceptions.py         # Custom exceptions
│
│   # Entity Platforms
├── sensor.py             # Sensor entities (resolution, bitrate, etc.)
├── binary_sensor.py      # Binary sensor entities (streaming state)
├── switch.py             # Switch entities (enable/disable streams)
├── button.py             # Button entities (reboot, etc.)
├── select.py             # Select entities (video mode)
│
│   # Supporting
├── services.py           # Custom services
├── diagnostics.py        # Diagnostic download
├── strings.json          # English translations
└── translations/
    └── en.json

tests/
├── conftest.py           # Test fixtures
├── test_init.py          # Setup tests
├── test_config_flow.py   # Config flow tests
├── test_coordinator.py   # Coordinator tests
├── test_api.py           # API client tests
├── test_sensor.py        # Sensor tests
└── ...                   # Additional test files
```

## manifest.json (2025 Format)

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

**Key fields:**
- `config_flow: true` - Required for UI setup
- `iot_class: local_polling` - ZowieBox uses HTTP polling
- No `integration_type` needed for device integrations

## __init__.py Pattern

```python
"""The Zowietek integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ZowietekCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]

type ZowietekConfigEntry = ConfigEntry[ZowietekCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
) -> bool:
    """Set up Zowietek from a config entry."""
    coordinator = ZowietekCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

## Config Flow Pattern

```python
"""Config flow for Zowietek integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

from .api import ZowietekClient, ZowietekAuthError, ZowietekConnectionError
from .const import DOMAIN, DEFAULT_USERNAME, DEFAULT_PASSWORD

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)


class ZowietekConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zowietek."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = ZowietekClient(
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )

            try:
                system_info = await client.async_get_system_info()
            except ZowietekAuthError:
                errors["base"] = "invalid_auth"
            except ZowietekConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(system_info["serial_number"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=system_info.get("device_name", "ZowieBox"),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
```

## Data Update Coordinator

```python
"""Data update coordinator for Zowietek."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import ZowietekClient, ZowietekApiError
from .const import DOMAIN
from .models import ZowietekData

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


class ZowietekCoordinator(DataUpdateCoordinator[ZowietekData]):
    """Class to manage fetching Zowietek data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = ZowietekClient(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )

    async def _async_update_data(self) -> ZowietekData:
        """Fetch data from ZowieBox."""
        try:
            system_info = await self.client.async_get_system_info()
            video_info = await self.client.async_get_video_info()
            stream_info = await self.client.async_get_stream_info()
            return ZowietekData(
                system=system_info,
                video=video_info,
                stream=stream_info,
            )
        except ZowietekApiError as err:
            raise UpdateFailed(f"Error communicating with ZowieBox: {err}") from err
```

## Entity Base Class

```python
"""Base entity for Zowietek."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZowietekCoordinator


class ZowietekEntity(CoordinatorEntity[ZowietekCoordinator]):
    """Base entity for Zowietek."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{device_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="Zowietek",
            model=self.coordinator.data.system.get("model", "ZowieBox"),
            name=self.coordinator.data.system.get("device_name", "ZowieBox"),
            sw_version=self.coordinator.data.system.get("firmware_version"),
        )
```

## Sensor Entity Example

```python
"""Sensor platform for Zowietek."""
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

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
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
        icon="mdi:speedometer",
    ),
    SensorEntityDescription(
        key="frame_rate",
        name="Frame Rate",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:camera-timer",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek sensors."""
    coordinator: ZowietekCoordinator = entry.runtime_data

    async_add_entities(
        ZowietekSensor(coordinator, entry.unique_id, description)
        for description in SENSOR_DESCRIPTIONS
    )


class ZowietekSensor(ZowietekEntity, SensorEntity):
    """Zowietek sensor entity."""

    entity_description: SensorEntityDescription

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
        return self.coordinator.data.video.get(self.entity_description.key)
```

## strings.json

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to ZowieBox",
        "description": "Enter your ZowieBox device details",
        "data": {
          "host": "Host or IP Address",
          "username": "Username",
          "password": "Password"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect to device",
      "invalid_auth": "Invalid username or password"
    },
    "abort": {
      "already_configured": "Device is already configured"
    }
  },
  "entity": {
    "sensor": {
      "video_resolution": {
        "name": "Video Resolution"
      },
      "stream_bitrate": {
        "name": "Stream Bitrate"
      },
      "frame_rate": {
        "name": "Frame Rate"
      }
    }
  }
}
```

## Async Best Practices

### Never Block the Event Loop

```python
# WRONG - Blocking I/O
def get_data(self) -> dict:
    response = requests.get(url)  # Blocks!
    return response.json()

# CORRECT - Async I/O
async def async_get_data(self) -> dict[str, str]:
    async with self._session.post(url, json=body) as response:
        return await response.json()
```

### Properties Never Do I/O

```python
# WRONG - Property makes network call
@property
def video_resolution(self) -> str | None:
    return self._client.get_video_info()["resolution"]  # Bad!

# CORRECT - Property returns cached data
@property
def video_resolution(self) -> str | None:
    return self.coordinator.data.video.get("resolution")
```

### Use Coordinator for Data Updates

```python
# Data comes from coordinator, not direct API calls
@property
def native_value(self) -> str | None:
    """Return the sensor value."""
    return self.coordinator.data.video.get("resolution")
```

## Error Handling

### ConfigEntryAuthFailed for Auth Errors

```python
from homeassistant.exceptions import ConfigEntryAuthFailed

async def _async_update_data(self) -> ZowietekData:
    try:
        return await self.client.async_get_all_data()
    except ZowietekAuthError as err:
        raise ConfigEntryAuthFailed(err) from err
    except ZowietekApiError as err:
        raise UpdateFailed(err) from err
```

## Testing Requirements

**100% coverage for:**
- `config_flow.py` - All steps, errors, abort cases
- `__init__.py` - Setup, unload, migration
- Entity state transitions
- Coordinator update failures

See **ha-zowietek-tdd** skill for testing patterns.

## The Bottom Line

**Follow current HA patterns exactly. Don't invent new patterns.**

- Config flow for setup
- Coordinator for data
- CoordinatorEntity base class
- Typed ConfigEntry with runtime_data
- Async everything, properties never do I/O
