"""Binary sensor platform for Zowietek integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from . import ZowietekConfigEntry
from .coordinator import ZowietekCoordinator
from .entity import ZowietekEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


@dataclass(frozen=True, kw_only=True)
class ZowietekBinarySensorEntityDescription(  # type: ignore[override]
    BinarySensorEntityDescription,
):
    """Describes a Zowietek binary sensor entity.

    Extends BinarySensorEntityDescription with sensor_type to identify
    what kind of binary state this sensor monitors.

    The type: ignore[override] is needed because frozen dataclasses
    generate __replace__ methods with incompatible signatures when
    extending other dataclasses. This is a known mypy limitation.
    """

    sensor_type: str
    """The type of binary sensor: 'streaming', 'video_input', 'ndi', 'rtmp', 'srt'."""


BINARY_SENSOR_DESCRIPTIONS: tuple[ZowietekBinarySensorEntityDescription, ...] = (
    ZowietekBinarySensorEntityDescription(
        key="streaming",
        translation_key="streaming",
        name="Streaming",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:broadcast",
        sensor_type="streaming",
    ),
    ZowietekBinarySensorEntityDescription(
        key="video_input",
        translation_key="video_input",
        name="Video input",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:video-input-hdmi",
        sensor_type="video_input",
    ),
    ZowietekBinarySensorEntityDescription(
        key="ndi_enabled",
        translation_key="ndi_enabled",
        name="NDI enabled",
        icon="mdi:broadcast",
        entity_category=EntityCategory.DIAGNOSTIC,
        sensor_type="ndi",
    ),
    ZowietekBinarySensorEntityDescription(
        key="rtmp_enabled",
        translation_key="rtmp_enabled",
        name="RTMP enabled",
        icon="mdi:upload-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        sensor_type="rtmp",
    ),
    ZowietekBinarySensorEntityDescription(
        key="srt_enabled",
        translation_key="srt_enabled",
        name="SRT enabled",
        icon="mdi:lan-connect",
        entity_category=EntityCategory.DIAGNOSTIC,
        sensor_type="srt",
    ),
)


class ZowietekBinarySensor(ZowietekEntity, BinarySensorEntity):
    """Zowietek binary sensor entity.

    Represents a binary sensor that displays on/off states for streaming,
    video input detection, and protocol enablement on the ZowieBox device.
    """

    entity_description: ZowietekBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        description: ZowietekBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor.

        Args:
            coordinator: The data update coordinator for this device.
            description: Entity description for this binary sensor.
        """
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on.

        Determines the state based on the sensor_type from the entity description.

        Returns:
            True if on, False if off, None if state is unknown.
        """
        if self.coordinator.data is None:
            return None

        sensor_type = self.entity_description.sensor_type

        if sensor_type == "streaming":
            return self._is_streaming()
        if sensor_type == "video_input":
            return self._has_video_input()
        if sensor_type == "ndi":
            return self._is_ndi_enabled()
        if sensor_type in ("rtmp", "srt"):
            return self._is_stream_protocol_enabled(sensor_type)

        return None

    def _is_streaming(self) -> bool:
        """Check if any streaming protocol is enabled.

        Returns:
            True if any of NDI, RTMP, or SRT is enabled.
        """
        # Check NDI
        if self._is_ndi_enabled():
            return True

        # Check RTMP and SRT
        if self._is_stream_protocol_enabled("rtmp"):
            return True
        if self._is_stream_protocol_enabled("srt"):
            return True

        return False

    def _has_video_input(self) -> bool:
        """Check if video input signal is detected.

        Supports both 'signal' and 'hdmi_signal' keys as different firmware
        versions may use different key names.

        Returns:
            True if video input signal is detected.
        """
        video_data = self.coordinator.data.video
        input_data = video_data.get("input")

        if not isinstance(input_data, dict):
            return False

        # Try 'signal' first, then fall back to 'hdmi_signal' for compatibility
        # with different firmware versions
        signal = input_data.get("signal")
        if signal is None:
            signal = input_data.get("hdmi_signal")

        if signal is None:
            return False

        # Handle both int and string values
        return str(signal) == "1"

    def _is_ndi_enabled(self) -> bool:
        """Check if NDI streaming is enabled.

        The NDI API returns 'switch' field for the enabled state.

        Returns:
            True if NDI is enabled.
        """
        stream_data = self.coordinator.data.stream
        # NDI API uses 'switch' field for enabled state
        ndi_switch = stream_data.get("switch")

        if ndi_switch is None:
            return False

        # Handle both int and string values
        return str(ndi_switch) == "1"

    def _is_stream_protocol_enabled(self, protocol: str) -> bool:
        """Check if a specific streaming protocol is enabled.

        Checks the publish list for entries matching the protocol type.
        The API uses 'switch' field for enabled state and 'type' for protocol.

        Args:
            protocol: The protocol type ('rtmp' or 'srt').

        Returns:
            True if the specified protocol is enabled.
        """
        stream_data = self.coordinator.data.stream
        publish_list = stream_data.get("publish")

        if not isinstance(publish_list, list):
            return False

        for entry in publish_list:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") == protocol:
                # API uses 'switch' field for enabled state
                switch = entry.get("switch")
                if switch is None:
                    return False
                # Handle both int and string values
                return str(switch) == "1"

        return False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek binary sensor entities.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for this integration instance.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    entities: list[ZowietekBinarySensor] = [
        ZowietekBinarySensor(coordinator, description) for description in BINARY_SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)
