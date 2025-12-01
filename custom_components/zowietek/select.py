"""Select platform for Zowietek integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.exceptions import HomeAssistantError

from . import ZowietekConfigEntry
from .coordinator import ZowietekCoordinator
from .entity import ZowietekEntity
from .exceptions import ZowietekApiError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

# Default output format options for fallback
DEFAULT_OUTPUT_FORMATS: list[str] = [
    "720p50",
    "720p60",
    "1080p50",
    "1080p60",
    "2160p30",
]


@dataclass(frozen=True, kw_only=True)
class ZowietekSelectEntityDescription(SelectEntityDescription):
    """Describes a Zowietek select entity.

    Extends SelectEntityDescription with select_type to identify
    which setting this select controls.
    """

    select_type: str
    """The select type: 'encoder_type' or 'output_format'."""


SELECT_DESCRIPTIONS: tuple[ZowietekSelectEntityDescription, ...] = (
    ZowietekSelectEntityDescription(
        key="encoder_type",
        translation_key="encoder_type",
        name="Encoder type",
        icon="mdi:video-box",
        select_type="encoder_type",
    ),
    ZowietekSelectEntityDescription(
        key="output_format",
        translation_key="output_format",
        name="Output format",
        icon="mdi:monitor",
        select_type="output_format",
    ),
)


class ZowietekSelect(ZowietekEntity, SelectEntity):
    """Zowietek select entity for device settings.

    Represents a select that controls settings like encoder type
    or output format on the ZowieBox device.
    """

    entity_description: ZowietekSelectEntityDescription

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        description: ZowietekSelectEntityDescription,
    ) -> None:
        """Initialize the select.

        Args:
            coordinator: The data update coordinator for this device.
            description: Entity description for this select.
        """
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option.

        Returns:
            The current option value, or None if not available.
        """
        if self.coordinator.data is None:
            return None

        select_type = self.entity_description.select_type

        if select_type == "encoder_type":
            return self._get_encoder_type_option()
        if select_type == "output_format":
            return self._get_output_format_option()

        return None

    def _get_encoder_type_option(self) -> str | None:
        """Get the current encoder type option.

        Returns:
            The current codec name, or None if not available.
        """
        video_data = self.coordinator.data.video
        codec_list = video_data.get("codec_list")
        codec_selected_id = video_data.get("codec_selected_id")

        if not isinstance(codec_list, list) or not codec_list:
            return None

        if not isinstance(codec_selected_id, int):
            return None

        if codec_selected_id < len(codec_list):
            return str(codec_list[codec_selected_id])

        return None

    def _get_output_format_option(self) -> str | None:
        """Get the current output format option.

        Returns:
            The current output format, or None if not available.
        """
        video_data = self.coordinator.data.video
        output_format = video_data.get("output_format")

        if output_format is not None:
            return str(output_format)

        return None

    @property
    def options(self) -> list[str]:
        """Return the available options.

        Returns:
            List of available option values.
        """
        if self.coordinator.data is None:
            return []

        select_type = self.entity_description.select_type

        if select_type == "encoder_type":
            return self._get_encoder_type_options()
        if select_type == "output_format":
            return self._get_output_format_options()

        return []

    def _get_encoder_type_options(self) -> list[str]:
        """Get the available encoder type options.

        Returns:
            List of available codec names.
        """
        video_data = self.coordinator.data.video
        codec_list = video_data.get("codec_list")

        if isinstance(codec_list, list):
            return [str(c) for c in codec_list]

        return []

    def _get_output_format_options(self) -> list[str]:
        """Get the available output format options.

        Returns:
            List of available output formats.
        """
        video_data = self.coordinator.data.video
        format_list = video_data.get("output_format_list")

        if isinstance(format_list, list) and format_list:
            return [str(f) for f in format_list]

        # Fallback: include current format and defaults
        current = video_data.get("output_format")
        options = list(DEFAULT_OUTPUT_FORMATS)
        if current and str(current) not in options:
            options.append(str(current))
        return options

    async def async_select_option(self, option: str) -> None:
        """Change the selected option.

        Args:
            option: The new option to select.

        Raises:
            HomeAssistantError: If the option cannot be set.
        """
        select_type = self.entity_description.select_type

        # Validate option is in available list
        if option not in self.options:
            raise HomeAssistantError(
                f"Invalid option '{option}' for {select_type}. Available options: {self.options}"
            )

        try:
            if select_type == "encoder_type":
                await self._set_encoder_type(option)
            elif select_type == "output_format":
                await self._set_output_format(option)
        except ZowietekApiError as err:
            _LOGGER.error("Failed to set %s to %s: %s", select_type, option, err)
            raise HomeAssistantError(f"Failed to set {select_type} to {option}: {err}") from err

        await self.coordinator.async_request_refresh()

    async def _set_encoder_type(self, option: str) -> None:
        """Set the encoder type.

        Args:
            option: The codec name to set.

        Raises:
            ZowietekApiError: If the API call fails.
        """
        # Find the codec_id for the selected option
        video_data = self.coordinator.data.video
        codec_list = video_data.get("codec_list")

        if not isinstance(codec_list, list):
            raise ZowietekApiError("Codec list not available", "00000")

        try:
            codec_id = codec_list.index(option)
        except ValueError as err:
            raise ZowietekApiError(f"Codec '{option}' not found", "00000") from err

        await self.coordinator.client.async_set_encoder_codec(codec_id)

    async def _set_output_format(self, option: str) -> None:
        """Set the output format.

        Args:
            option: The output format to set (e.g., "1080p60").

        Raises:
            ZowietekApiError: If the API call fails.
        """
        await self.coordinator.client.async_set_output_format(option)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek select entities.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for this integration instance.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    entities: list[ZowietekSelect] = [
        ZowietekSelect(coordinator, description) for description in SELECT_DESCRIPTIONS
    ]

    async_add_entities(entities)
