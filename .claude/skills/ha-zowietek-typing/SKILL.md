---
name: ha-zowietek-typing
description: Use when writing ANY Python code for the HA Zowietek integration - enforces strict typing with ZERO Any usage, proper type annotations for all functions, TypedDicts for data structures, and mypy strict compliance.
---

# Home Assistant Zowietek Strict Typing

## Overview

**NEVER use `Any`. Every type must be explicit and correct.**

This integration follows Home Assistant's strict typing requirements. All code must pass mypy with `--strict`.

## The Iron Law

```
NO Any TYPE. EVER.
```

**Exceptions for `Any`:**
- None

**Not even for:**
- "Complex nested data"
- "Third-party library returns Any"
- "It's just kwargs"
- "The type is too complicated"

If you think you need `Any`, you need a TypedDict, Protocol, or Generic instead.

## Type Annotation Requirements

### Every Function Must Be Fully Typed

```python
# WRONG - Missing types
def process_video(data):
    return data["resolution"]

# WRONG - Uses Any
def process_video(data: Any) -> Any:
    return data["resolution"]

# CORRECT - Explicit types
def process_video(data: ZowietekVideoInfo) -> str:
    return data["resolution"]
```

### All Class Attributes Must Be Typed

```python
# WRONG - No type annotations
class ZowietekSensor:
    def __init__(self, client, device):
        self._client = client
        self._device = device
        self._state = None

# CORRECT - All types explicit
class ZowietekSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        device_id: str,
    ) -> None:
        self._coordinator: ZowietekCoordinator = coordinator
        self._device_id: str = device_id
        self._attr_native_value: str | int | float | None = None
```

## TypedDict for API Responses

When ZowieBox API returns JSON dictionaries, define TypedDicts:

```python
from typing import TypedDict, NotRequired

class ZowietekSystemInfo(TypedDict):
    """Type for ZowieBox system information response."""
    status: str
    rsp: str
    device_name: NotRequired[str]
    firmware_version: NotRequired[str]
    model: NotRequired[str]
    serial_number: NotRequired[str]
    uptime: NotRequired[int]


class ZowietekVideoInfo(TypedDict):
    """Type for video settings response."""
    status: str
    rsp: str
    input_source: NotRequired[str]
    resolution: NotRequired[str]
    frame_rate: NotRequired[int]
    encoder_type: NotRequired[str]
    bitrate: NotRequired[int]


class ZowietekStreamInfo(TypedDict):
    """Type for stream settings response."""
    status: str
    rsp: str
    ndi_enabled: NotRequired[bool]
    ndi_name: NotRequired[str]
    rtmp_url: NotRequired[str]
    rtmp_enabled: NotRequired[bool]
    srt_enabled: NotRequired[bool]
```

## Dataclasses for Internal Models

Convert API responses to typed dataclasses:

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ZowietekDevice:
    """Internal representation of a ZowieBox device."""
    host: str
    name: str
    model: str
    firmware: str
    serial: str

    @classmethod
    def from_api(cls, host: str, data: ZowietekSystemInfo) -> ZowietekDevice:
        """Create from API response."""
        return cls(
            host=host,
            name=data.get("device_name", "ZowieBox"),
            model=data.get("model", "Unknown"),
            firmware=data.get("firmware_version", "Unknown"),
            serial=data.get("serial_number", "Unknown"),
        )


@dataclass(frozen=True, slots=True)
class VideoState:
    """Internal representation of video state."""
    resolution: str
    frame_rate: int
    encoder_type: str
    bitrate: int

    @classmethod
    def from_api(cls, data: ZowietekVideoInfo) -> VideoState:
        """Create from API response."""
        return cls(
            resolution=data.get("resolution", "Unknown"),
            frame_rate=data.get("frame_rate", 0),
            encoder_type=data.get("encoder_type", "Unknown"),
            bitrate=data.get("bitrate", 0),
        )
```

## Custom ConfigEntry Type

**Required** for runtime data:

```python
from homeassistant.config_entries import ConfigEntry

from .coordinator import ZowietekCoordinator

type ZowietekConfigEntry = ConfigEntry[ZowietekCoordinator]
```

Use throughout the integration:

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
) -> bool:
    """Set up Zowietek from a config entry."""
    coordinator = ZowietekCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # ...
```

## Handling Optional Values

Use `| None` syntax (not `Optional`):

```python
# WRONG - Old style
from typing import Optional
def get_resolution(self) -> Optional[str]:
    return self._resolution

# CORRECT - Modern union syntax
def get_resolution(self) -> str | None:
    return self._resolution
```

## Generic Types

Use generics for containers:

```python
# WRONG - Bare list/dict
def get_streams() -> list:
    ...

def get_settings() -> dict:
    ...

# CORRECT - Typed containers
def get_streams() -> list[ZowietekStream]:
    ...

def get_settings() -> dict[str, str]:
    ...
```

## Callback and Callable Types

```python
from collections.abc import Callable, Awaitable

# Sync callback
StateCallback = Callable[[str], None]

# Async callback
AsyncStateCallback = Callable[[str], Awaitable[None]]

# With optional args
UpdateCallback = Callable[[str, dict[str, str] | None], None]
```

## Protocol for Duck Typing

When you need interface-like behavior:

```python
from typing import Protocol

class SupportsStreaming(Protocol):
    """Protocol for objects that support streaming."""

    async def async_start_stream(self) -> None: ...
    async def async_stop_stream(self) -> None: ...
    @property
    def is_streaming(self) -> bool: ...


def control_stream(device: SupportsStreaming) -> None:
    """Control any object supporting streaming."""
    ...
```

## Kwargs Handling

For methods requiring `**kwargs` (like HA interfaces):

```python
from typing import Unpack

class ServiceCallKwargs(TypedDict, total=False):
    """Kwargs for service calls."""
    target_resolution: str
    bitrate: int


async def async_set_video_settings(
    self,
    **kwargs: Unpack[ServiceCallKwargs],
) -> None:
    """Set video settings."""
    resolution = kwargs.get("target_resolution")
    bitrate = kwargs.get("bitrate")
```

If true Any kwargs are required by parent interface, use explicit comment:

```python
async def async_turn_on(
    self,
    **kwargs: Any,  # Required by SwitchEntity interface
) -> None:
```

This is the **only** acceptable use of Any - when overriding a base class method that requires it.

## Mypy Configuration

In `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_unreachable = true
warn_return_any = true
disallow_any_generics = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true

[[tool.mypy.overrides]]
module = "homeassistant.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "aiohttp.*"
ignore_missing_imports = true
```

## Common Type Errors and Fixes

### "has no attribute" on Union

```python
# ERROR: Item "None" has no attribute "resolution"
def get_resolution(info: ZowietekVideoInfo | None) -> str:
    return info["resolution"]  # Error!

# FIX: Guard the None case
def get_resolution(info: ZowietekVideoInfo | None) -> str | None:
    if info is None:
        return None
    return info.get("resolution")
```

### "Incompatible return type"

```python
# ERROR: list[str] vs list[Any]
def get_sources(self) -> list[str]:
    return self._sources  # Error if _sources is list[Any]

# FIX: Type the attribute properly
self._sources: list[str] = []
```

### External Library Returns Any

```python
# BAD: Let Any propagate
result = external_lib.get_data()  # Returns Any
self._data = result  # Now _data is Any

# GOOD: Parse into typed structure immediately
raw = external_lib.get_data()
self._data = parse_to_typed(raw)  # Returns TypedDict or dataclass
```

## Red Flags - Type Violations

Stop and fix if you see ANY of these:

- `Any` in a type annotation
- `# type: ignore` without error code
- Untyped function or method
- `cast()` to bypass type checking
- `dict` or `list` without type parameters
- Variables without type annotations in class `__init__`

## The Bottom Line

**Every type explicit. Zero Any. Mypy strict passes.**

If the type is hard to express, that's a sign to create proper TypedDicts, dataclasses, or Protocols.

No shortcuts. No Any. No excuses.
