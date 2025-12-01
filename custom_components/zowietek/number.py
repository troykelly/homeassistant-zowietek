"""Number platform for Zowietek integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, UnitOfDataRate
from homeassistant.exceptions import HomeAssistantError

from . import ZowietekConfigEntry
from .coordinator import ZowietekCoordinator
from .entity import ZowietekEntity
from .exceptions import ZowietekApiError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ZowietekNumberEntityDescription(NumberEntityDescription):  # type: ignore[override]
    """Describes a Zowietek number entity.

    Extends NumberEntityDescription with number_type to identify
    which setting this number controls.
    """

    number_type: str
    """The number type: 'audio_volume' or 'stream_bitrate'."""


NUMBER_DESCRIPTIONS: tuple[ZowietekNumberEntityDescription, ...] = (
    ZowietekNumberEntityDescription(
        key="audio_volume",
        translation_key="audio_volume",
        name="Audio volume",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:volume-high",
        mode=NumberMode.SLIDER,
        number_type="audio_volume",
    ),
    ZowietekNumberEntityDescription(
        key="stream_bitrate",
        translation_key="stream_bitrate",
        name="Stream bitrate",
        native_min_value=1,
        native_max_value=50,
        native_step=1,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        icon="mdi:speedometer",
        mode=NumberMode.SLIDER,
        number_type="stream_bitrate",
    ),
)


class ZowietekNumber(ZowietekEntity, NumberEntity):
    """Zowietek number entity for device settings.

    Represents a number that controls settings like audio volume
    or stream bitrate on the ZowieBox device.
    """

    entity_description: ZowietekNumberEntityDescription

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        description: ZowietekNumberEntityDescription,
    ) -> None:
        """Initialize the number.

        Args:
            coordinator: The data update coordinator for this device.
            description: Entity description for this number.
        """
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current value.

        Returns:
            The current value, or None if not available.
        """
        if self.coordinator.data is None:
            return None

        number_type = self.entity_description.number_type

        if number_type == "audio_volume":
            return self._get_audio_volume_value()
        if number_type == "stream_bitrate":
            return self._get_stream_bitrate_value()

        return None

    def _get_audio_volume_value(self) -> float | None:
        """Get the current audio volume value.

        Returns:
            The current volume (0-100), or None if not available.
        """
        audio_data = self.coordinator.data.audio
        volume = audio_data.get("volume")

        if volume is not None and isinstance(volume, int | float):
            return float(volume)

        return None

    def _get_stream_bitrate_value(self) -> float | None:
        """Get the current stream bitrate value in Mbps.

        Returns:
            The current bitrate in Mbps, or None if not available.
        """
        video_data = self.coordinator.data.video
        bitrate = video_data.get("enc_bitrate")

        if bitrate is not None and isinstance(bitrate, int | float):
            # Convert from bps to Mbps
            return float(bitrate) / 1_000_000

        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value.

        Args:
            value: The new value to set.

        Raises:
            HomeAssistantError: If the value cannot be set.
        """
        number_type = self.entity_description.number_type

        try:
            if number_type == "audio_volume":
                await self._set_audio_volume(int(value))
            elif number_type == "stream_bitrate":
                await self._set_stream_bitrate(value)
        except ZowietekApiError as err:
            _LOGGER.error("Failed to set %s to %s: %s", number_type, value, err)
            raise HomeAssistantError(f"Failed to set {number_type} to {value}: {err}") from err

        await self.coordinator.async_request_refresh()

    async def _set_audio_volume(self, value: int) -> None:
        """Set the audio volume.

        Args:
            value: The volume to set (0-100).

        Raises:
            ZowietekApiError: If the API call fails.
        """
        await self.coordinator.client.async_set_audio_volume(value)

    async def _set_stream_bitrate(self, value: float) -> None:
        """Set the stream bitrate.

        Args:
            value: The bitrate to set in Mbps.

        Raises:
            ZowietekApiError: If the API call fails.
        """
        # Convert from Mbps to bps
        bitrate_bps = int(value * 1_000_000)
        await self.coordinator.client.async_set_encoder_bitrate(bitrate_bps)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek number entities.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for this integration instance.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    entities: list[ZowietekNumber] = [
        ZowietekNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS
    ]

    async_add_entities(entities)
