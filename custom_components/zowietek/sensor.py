"""Sensor platform for Zowietek integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.typing import StateType

from . import ZowietekConfigEntry
from .coordinator import ZowietekCoordinator
from .entity import ZowietekEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


@dataclass(frozen=True, kw_only=True)
class ZowietekSensorEntityDescription(  # type: ignore[override]
    SensorEntityDescription,
):
    """Describes a Zowietek sensor entity.

    Extends SensorEntityDescription with a value_key to extract
    the sensor value from coordinator data.

    The type: ignore[override] is needed because frozen dataclasses
    generate __replace__ methods with incompatible signatures when
    extending other dataclasses. This is a known mypy limitation.
    """

    value_key: str
    """Key path to extract value from coordinator data.

    Format: "section.key" where section is one of: system, video, stream, audio, network
    and key is the specific data key.
    """


SENSOR_DESCRIPTIONS: tuple[ZowietekSensorEntityDescription, ...] = (
    ZowietekSensorEntityDescription(
        key="video_resolution",
        translation_key="video_resolution",
        name="Video resolution",
        icon="mdi:video",
        value_key="video.enc_resolution",
    ),
    ZowietekSensorEntityDescription(
        key="frame_rate",
        translation_key="frame_rate",
        name="Frame rate",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:camera-timer",
        value_key="video.enc_framerate",
    ),
    ZowietekSensorEntityDescription(
        key="stream_bitrate",
        translation_key="stream_bitrate",
        name="Stream bitrate",
        native_unit_of_measurement="bps",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_key="video.enc_bitrate",
    ),
    ZowietekSensorEntityDescription(
        key="encoder_type",
        translation_key="encoder_type",
        name="Encoder type",
        icon="mdi:video-box",
        value_key="video.enc_type",
    ),
    ZowietekSensorEntityDescription(
        key="ndi_name",
        translation_key="ndi_name",
        name="NDI name",
        icon="mdi:broadcast",
        value_key="stream.ndi_name",
    ),
    ZowietekSensorEntityDescription(
        key="output_format",
        translation_key="output_format",
        name="Output format",
        icon="mdi:monitor",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_key="video.output_format",
    ),
    # System information sensors
    ZowietekSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        name="Firmware version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_key="system.firmware_version",
    ),
    ZowietekSensorEntityDescription(
        key="hardware_version",
        translation_key="hardware_version",
        name="Hardware version",
        icon="mdi:memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_key="system.hardware_version",
    ),
    ZowietekSensorEntityDescription(
        key="serial_number",
        translation_key="serial_number",
        name="Serial number",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_key="system.devicesn",
    ),
    # Dashboard sensors
    ZowietekSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_key="dashboard.uptime",
    ),
    ZowietekSensorEntityDescription(
        key="cpu_temperature",
        translation_key="cpu_temperature",
        name="CPU temperature",
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_key="dashboard.cpu_temp",
    ),
    ZowietekSensorEntityDescription(
        key="cpu_usage",
        translation_key="cpu_usage",
        name="CPU usage",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:cpu-64-bit",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_key="dashboard.cpu_usage",
    ),
)


class ZowietekSensor(ZowietekEntity, SensorEntity):
    """Zowietek sensor entity.

    Represents a sensor that displays status information from the
    ZowieBox device such as video resolution, frame rate, etc.
    """

    entity_description: ZowietekSensorEntityDescription

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        description: ZowietekSensorEntityDescription,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The data update coordinator for this device.
            description: Entity description for this sensor.
        """
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the sensor value.

        Extracts the value from coordinator data using the value_key
        from the entity description.

        Returns:
            The sensor value, or None if not available.
        """
        # Parse value_key (format: "section.key")
        parts = self.entity_description.value_key.split(".", 1)
        if len(parts) != 2:
            return None

        section, key = parts

        # Get the data section from coordinator
        data = self.coordinator.data
        if data is None:
            return None

        section_data = getattr(data, section, None)
        if section_data is None or not isinstance(section_data, dict):
            return None

        # Get the value from the section
        value = section_data.get(key)
        if value is None:
            return None

        # Value is str | int from ZowietekData, both are valid StateType
        if isinstance(value, (str, int, float)):
            return value
        # Convert other types to string
        return str(value)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek sensor entities.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for this integration instance.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    entities: list[ZowietekSensor] = [
        ZowietekSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)
