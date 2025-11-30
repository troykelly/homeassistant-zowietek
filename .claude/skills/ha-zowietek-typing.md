---
name: ha-zowietek-typing
description: Type safety rules for Zowietek integration - no Any types allowed
---

# Type Safety Rules

## The Rule

**NEVER use `Any` in type annotations.**

The only exception: `**kwargs: Any` when overriding Home Assistant base class methods that require it.

## Use TypedDict for API Responses

```python
from typing import TypedDict, NotRequired

class ZowietekSystemInfo(TypedDict):
    """ZowieBox system information response."""
    status: str
    rsp: str
    device_name: NotRequired[str]
    firmware_version: NotRequired[str]
    model: NotRequired[str]
    serial_number: NotRequired[str]
    uptime: NotRequired[int]

class ZowietekVideoSettings(TypedDict):
    """ZowieBox video settings response."""
    status: str
    rsp: str
    input_source: NotRequired[str]
    resolution: NotRequired[str]
    frame_rate: NotRequired[int]
    encoder_type: NotRequired[str]
    bitrate: NotRequired[int]

class ZowietekStreamSettings(TypedDict):
    """ZowieBox stream settings response."""
    status: str
    rsp: str
    ndi_enabled: NotRequired[bool]
    ndi_name: NotRequired[str]
    rtmp_url: NotRequired[str]
    rtmp_enabled: NotRequired[bool]
    srt_enabled: NotRequired[bool]
```

## Use dataclasses for Internal Models

```python
from dataclasses import dataclass

@dataclass
class ZowietekDevice:
    """Internal representation of a ZowieBox device."""
    host: str
    name: str
    model: str
    firmware: str
    serial: str

    @classmethod
    def from_api_response(cls, host: str, data: ZowietekSystemInfo) -> ZowietekDevice:
        """Create device from API response."""
        return cls(
            host=host,
            name=data.get("device_name", "ZowieBox"),
            model=data.get("model", "Unknown"),
            firmware=data.get("firmware_version", "Unknown"),
            serial=data.get("serial_number", "Unknown"),
        )
```

## Use Protocol for Interfaces

```python
from typing import Protocol

class ZowietekAPIProtocol(Protocol):
    """Protocol for ZowieBox API clients."""

    async def login(self) -> bool:
        """Authenticate with the device."""
        ...

    async def get_system_info(self) -> ZowietekSystemInfo:
        """Get system information."""
        ...

    async def get_video_settings(self) -> ZowietekVideoSettings:
        """Get video settings."""
        ...
```

## Modern Type Syntax

```python
# CORRECT - Use modern union syntax
def get_device(device_id: str) -> ZowietekDevice | None:
    pass

# WRONG - Don't use Optional
from typing import Optional
def get_device(device_id: str) -> Optional[ZowietekDevice]:  # NO!
    pass

# CORRECT - Use | for unions
def process_value(value: str | int | float) -> str:
    pass

# CORRECT - Use list, dict, set directly
def get_devices() -> list[ZowietekDevice]:
    pass

# WRONG - Don't import from typing
from typing import List  # NO!
def get_devices() -> List[ZowietekDevice]:  # NO!
    pass
```

## Entity Attributes

```python
class ZowietekSensor(CoordinatorEntity, SensorEntity):
    """Zowietek sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        device: ZowietekDevice,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{device.serial}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.serial)},
            name=device.name,
            manufacturer="Zowietek",
            model=device.model,
            sw_version=device.firmware,
        )

    @property
    def native_value(self) -> str | int | float | None:
        """Return the sensor value."""
        return self.coordinator.data.get(self.entity_description.key)
```

## Mypy Configuration

The project uses strict mypy settings:

```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_any_generics = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
```
