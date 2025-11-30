---
name: ha-zowietek-video-encoder
description: Use when implementing ZowieBox-specific features - covers device capabilities, API endpoints, entity mappings, video/audio/stream settings, and NDI/RTMP/SRT protocols for the 4K HDMI NDI Video Encoder/Decoder.
---

# Home Assistant Zowietek Video Encoder

## Overview

**Implement ZowieBox-specific features following the device API and capabilities.**

This covers the ZowieBox 4K HDMI NDI Video Encoder/Decoder hardware, API structure, entity mappings, and implementation details.

## Device Overview

The ZowieBox is a professional video streaming device supporting:

### Encoder Mode
- HDMI input to NDI|HX3 output
- HDMI input to RTMP/RTSP/SRT stream
- Up to 4K30 encoding
- 4K60 loop-through

### Decoder Mode
- NDI|HX3 input to HDMI output
- RTSP/SRT/RTMP input to HDMI output
- UVC input to HDMI output
- Up to 4K30 decoding

## ZowieBox API Reference

### Authentication

```python
# Login endpoint
POST /system?option=setinfo&login_check_flag=1
Content-Type: application/json
{"group": "user", "user": "admin", "psw": "admin"}

# Response
{"status": "00000", "rsp": "succeed"}
```

### Status Codes

| Code | Meaning |
|------|---------|
| `00000` | Success |
| `00003` | Invalid parameters |
| `80003` | Not logged in / authentication required |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/system?option=getinfo` | POST | System information |
| `/system?option=setinfo` | POST | Update system settings |
| `/video?option=getinfo` | POST | Video input/output settings |
| `/video?option=setinfo` | POST | Update video settings |
| `/audio?option=getinfo` | POST | Audio settings |
| `/audio?option=setinfo` | POST | Update audio settings |
| `/network?option=getinfo` | POST | Network configuration |
| `/network?option=setinfo` | POST | Update network settings |
| `/stream?option=getinfo` | POST | NDI/RTMP/SRT stream settings |
| `/stream?option=setinfo` | POST | Update stream settings |
| `/streamplay?option=getinfo` | POST | Decoder playback settings |
| `/streamplay?option=setinfo` | POST | Update playback settings |
| `/third_api?option=getinfo` | POST | Third-party API configuration |

### Request Format

All requests require a JSON body with a `group` field:

```python
# Basic request (may require auth)
{"group": "all"}

# Authenticated request
{"group": "all", "user": "admin", "psw": "admin"}
```

## Entity Mapping

### Sensor Entities

| Entity | API Source | Description |
|--------|-----------|-------------|
| `sensor.{device}_video_resolution` | video.resolution | Current video resolution |
| `sensor.{device}_frame_rate` | video.frame_rate | Current frame rate |
| `sensor.{device}_stream_bitrate` | stream.bitrate | Stream bitrate (Mbps) |
| `sensor.{device}_encoder_type` | video.encoder_type | H.264/H.265 |
| `sensor.{device}_ndi_name` | stream.ndi_name | NDI stream name |
| `sensor.{device}_firmware_version` | system.firmware_version | Device firmware |
| `sensor.{device}_uptime` | system.uptime | Device uptime |

### Binary Sensor Entities

| Entity | API Source | Description |
|--------|-----------|-------------|
| `binary_sensor.{device}_streaming` | stream.enabled | Stream active |
| `binary_sensor.{device}_ndi_enabled` | stream.ndi_enabled | NDI output enabled |
| `binary_sensor.{device}_rtmp_enabled` | stream.rtmp_enabled | RTMP output enabled |
| `binary_sensor.{device}_video_input` | video.input_detected | HDMI signal detected |

### Switch Entities

| Entity | API Endpoint | Description |
|--------|-------------|-------------|
| `switch.{device}_ndi_stream` | stream.ndi_enabled | Enable/disable NDI |
| `switch.{device}_rtmp_stream` | stream.rtmp_enabled | Enable/disable RTMP |
| `switch.{device}_srt_stream` | stream.srt_enabled | Enable/disable SRT |

### Button Entities

| Entity | API Action | Description |
|--------|-----------|-------------|
| `button.{device}_reboot` | system.reboot | Reboot device |
| `button.{device}_refresh` | coordinator.refresh | Force data refresh |

### Select Entities

| Entity | API Field | Options |
|--------|----------|---------|
| `select.{device}_video_mode` | video.mode | encoder, decoder |
| `select.{device}_resolution` | video.resolution | 4K30, 1080p60, etc. |
| `select.{device}_encoder_type` | video.encoder_type | H.264, H.265 |

## TypedDict Definitions

```python
from typing import TypedDict, NotRequired

class ZowietekSystemInfo(TypedDict):
    """System information response."""
    status: str
    rsp: str
    device_name: NotRequired[str]
    model: NotRequired[str]
    serial_number: NotRequired[str]
    firmware_version: NotRequired[str]
    uptime: NotRequired[int]


class ZowietekVideoInfo(TypedDict):
    """Video settings response."""
    status: str
    rsp: str
    mode: NotRequired[str]  # "encoder" or "decoder"
    input_source: NotRequired[str]
    resolution: NotRequired[str]
    frame_rate: NotRequired[int]
    encoder_type: NotRequired[str]  # "H.264" or "H.265"
    bitrate: NotRequired[int]
    input_detected: NotRequired[bool]


class ZowietekAudioInfo(TypedDict):
    """Audio settings response."""
    status: str
    rsp: str
    input_source: NotRequired[str]
    codec: NotRequired[str]
    sample_rate: NotRequired[int]
    channels: NotRequired[int]
    volume: NotRequired[int]


class ZowietekStreamInfo(TypedDict):
    """Stream settings response."""
    status: str
    rsp: str
    ndi_enabled: NotRequired[bool]
    ndi_name: NotRequired[str]
    ndi_group: NotRequired[str]
    rtmp_enabled: NotRequired[bool]
    rtmp_url: NotRequired[str]
    srt_enabled: NotRequired[bool]
    srt_port: NotRequired[int]
    srt_latency: NotRequired[int]
    bitrate: NotRequired[int]


class ZowietekNetworkInfo(TypedDict):
    """Network settings response."""
    status: str
    rsp: str
    ip_address: NotRequired[str]
    subnet_mask: NotRequired[str]
    gateway: NotRequired[str]
    mac_address: NotRequired[str]
    dhcp_enabled: NotRequired[bool]
```

## API Client Implementation

```python
"""ZowieBox API client."""
from __future__ import annotations

import aiohttp
from typing import TYPE_CHECKING

from .const import STATUS_SUCCESS, STATUS_NOT_LOGGED_IN
from .exceptions import ZowietekAuthError, ZowietekConnectionError, ZowietekApiError

if TYPE_CHECKING:
    from .models import ZowietekSystemInfo, ZowietekVideoInfo, ZowietekStreamInfo


class ZowietekClient:
    """Client for ZowieBox API."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the client."""
        self._host = host.rstrip("/")
        self._username = username
        self._password = password
        self._session = session
        self._owns_session = session is None

    async def _request(
        self,
        endpoint: str,
        data: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Make authenticated API request."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True

        url = f"{self._host}/{endpoint}"
        body = {
            "group": "all",
            "user": self._username,
            "psw": self._password,
        }
        if data:
            body.update(data)

        try:
            async with self._session.post(url, json=body) as response:
                result = await response.json()

                if result.get("status") == STATUS_NOT_LOGGED_IN:
                    raise ZowietekAuthError("Authentication failed")

                if result.get("status") != STATUS_SUCCESS:
                    raise ZowietekApiError(f"API error: {result}")

                return result

        except aiohttp.ClientError as err:
            raise ZowietekConnectionError(f"Connection failed: {err}") from err

    async def async_get_system_info(self) -> ZowietekSystemInfo:
        """Get system information."""
        return await self._request("system?option=getinfo")

    async def async_get_video_info(self) -> ZowietekVideoInfo:
        """Get video settings."""
        return await self._request("video?option=getinfo")

    async def async_get_stream_info(self) -> ZowietekStreamInfo:
        """Get stream settings."""
        return await self._request("stream?option=getinfo")

    async def async_set_ndi_enabled(self, enabled: bool) -> None:
        """Enable or disable NDI stream."""
        await self._request(
            "stream?option=setinfo",
            {"ndi_enabled": "1" if enabled else "0"},
        )

    async def close(self) -> None:
        """Close the session."""
        if self._owns_session and self._session:
            await self._session.close()
```

## Sensor Implementation Example

```python
"""Sensor platform for Zowietek."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfDataRate

from .entity import ZowietekEntity

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="video_resolution",
        translation_key="video_resolution",
        icon="mdi:video",
    ),
    SensorEntityDescription(
        key="frame_rate",
        translation_key="frame_rate",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:camera-timer",
    ),
    SensorEntityDescription(
        key="stream_bitrate",
        translation_key="stream_bitrate",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
    SensorEntityDescription(
        key="encoder_type",
        translation_key="encoder_type",
        icon="mdi:video-box",
    ),
    SensorEntityDescription(
        key="ndi_name",
        translation_key="ndi_name",
        icon="mdi:broadcast",
    ),
)


class ZowietekSensor(ZowietekEntity, SensorEntity):
    """Zowietek sensor entity."""

    entity_description: SensorEntityDescription

    @property
    def native_value(self) -> str | int | float | None:
        """Return the sensor value."""
        key = self.entity_description.key

        # Map keys to coordinator data
        if key == "video_resolution":
            return self.coordinator.data.video.get("resolution")
        if key == "frame_rate":
            return self.coordinator.data.video.get("frame_rate")
        if key == "stream_bitrate":
            return self.coordinator.data.stream.get("bitrate")
        if key == "encoder_type":
            return self.coordinator.data.video.get("encoder_type")
        if key == "ndi_name":
            return self.coordinator.data.stream.get("ndi_name")

        return None
```

## Switch Implementation Example

```python
"""Switch platform for Zowietek."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

from .entity import ZowietekEntity


class ZowietekSwitch(ZowietekEntity, SwitchEntity):
    """Zowietek switch entity for stream control."""

    entity_description: SwitchEntityDescription

    @property
    def is_on(self) -> bool:
        """Return true if stream is enabled."""
        key = self.entity_description.key
        return bool(self.coordinator.data.stream.get(f"{key}_enabled"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the stream."""
        key = self.entity_description.key
        await self.coordinator.client.async_set_stream_enabled(key, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the stream."""
        key = self.entity_description.key
        await self.coordinator.client.async_set_stream_enabled(key, False)
        await self.coordinator.async_request_refresh()
```

## Common Patterns

### Handling Optional API Fields

```python
# API may not return all fields
resolution = self.coordinator.data.video.get("resolution", "Unknown")
frame_rate = self.coordinator.data.video.get("frame_rate")  # May be None
```

### Enum Values

```python
from enum import StrEnum

class VideoMode(StrEnum):
    """Video operating mode."""
    ENCODER = "encoder"
    DECODER = "decoder"

class EncoderType(StrEnum):
    """Video encoder type."""
    H264 = "H.264"
    H265 = "H.265"
```

### Unit Conversions

```python
# Bitrate may come in various units
def normalize_bitrate(value: int, unit: str) -> float:
    """Convert bitrate to Mbps."""
    if unit == "kbps":
        return value / 1000
    if unit == "bps":
        return value / 1_000_000
    return float(value)  # Assume Mbps
```

## Testing Patterns

### Mock API Responses

```python
@pytest.fixture
def mock_system_info() -> ZowietekSystemInfo:
    """Return mock system info."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "device_name": "ZowieBox Living Room",
        "model": "ZB-4K",
        "serial_number": "ZB123456",
        "firmware_version": "1.0.0",
        "uptime": 86400,
    }

@pytest.fixture
def mock_video_info() -> ZowietekVideoInfo:
    """Return mock video info."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "mode": "encoder",
        "resolution": "3840x2160",
        "frame_rate": 30,
        "encoder_type": "H.265",
        "bitrate": 20,
        "input_detected": True,
    }
```

## The Bottom Line

**Map ZowieBox capabilities to HA entities correctly.**

- Use TypedDict for all API responses
- Handle optional fields gracefully
- Implement switches for stream control
- Sensors for monitoring state
- Follow device modes (encoder/decoder)
- Test with live devices when possible
