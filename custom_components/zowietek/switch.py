"""Switch platform for Zowietek integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
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


@dataclass(frozen=True, kw_only=True)
class ZowietekSwitchEntityDescription(  # type: ignore[override]
    SwitchEntityDescription,
):
    """Describes a Zowietek switch entity.

    Extends SwitchEntityDescription with stream_type to identify
    which streaming protocol this switch controls.

    The type: ignore[override] is needed because frozen dataclasses
    generate __replace__ methods with incompatible signatures when
    extending other dataclasses. This is a known mypy limitation.
    """

    stream_type: str
    """The stream protocol type: 'ndi', 'rtmp', or 'srt'."""


SWITCH_DESCRIPTIONS: tuple[ZowietekSwitchEntityDescription, ...] = (
    ZowietekSwitchEntityDescription(
        key="ndi_stream",
        translation_key="ndi_stream",
        name="NDI stream",
        icon="mdi:broadcast",
        stream_type="ndi",
    ),
    ZowietekSwitchEntityDescription(
        key="rtmp_stream",
        translation_key="rtmp_stream",
        name="RTMP stream",
        icon="mdi:upload-network",
        stream_type="rtmp",
    ),
    ZowietekSwitchEntityDescription(
        key="srt_stream",
        translation_key="srt_stream",
        name="SRT stream",
        icon="mdi:lan-connect",
        stream_type="srt",
    ),
)


class ZowietekSwitch(ZowietekEntity, SwitchEntity):
    """Zowietek switch entity for stream control.

    Represents a switch that controls enabling/disabling stream outputs
    (NDI, RTMP, SRT) on the ZowieBox device.
    """

    entity_description: ZowietekSwitchEntityDescription

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        description: ZowietekSwitchEntityDescription,
    ) -> None:
        """Initialize the switch.

        Args:
            coordinator: The data update coordinator for this device.
            description: Entity description for this switch.
        """
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return true if the stream is enabled.

        Checks the coordinator data to determine if the corresponding
        stream type is currently enabled on the device.

        Returns:
            True if the stream is enabled, False otherwise.
        """
        if self.coordinator.data is None:
            return False

        stream_type = self.entity_description.stream_type
        stream_data = self.coordinator.data.stream

        if stream_type == "ndi":
            # NDI enabled state is in ndi_enable field
            ndi_enable = stream_data.get("ndi_enable")
            if ndi_enable is None:
                return False
            # Handle both int and string values
            return str(ndi_enable) == "1"

        # For RTMP and SRT, check the publish list
        publish_list = stream_data.get("publish")
        if not isinstance(publish_list, list):
            return False

        for entry in publish_list:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") == stream_type:
                enable = entry.get("enable")
                if enable is None:
                    return False
                # Handle both int and string values
                return str(enable) == "1"

        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the stream.

        Calls the appropriate API method to enable the stream
        and requests a coordinator refresh.

        Args:
            kwargs: Additional arguments (required by HA interface).

        Raises:
            HomeAssistantError: If the stream cannot be enabled.
        """
        stream_type = self.entity_description.stream_type

        try:
            if stream_type == "ndi":
                await self.coordinator.client.async_set_ndi_enabled(True)
            else:
                await self.coordinator.client.async_set_stream_enabled(stream_type, True)
        except ZowietekApiError as err:
            _LOGGER.error("Failed to enable %s stream: %s", stream_type, err)
            raise HomeAssistantError(f"Failed to enable {stream_type} stream: {err}") from err

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the stream.

        Calls the appropriate API method to disable the stream
        and requests a coordinator refresh.

        Args:
            kwargs: Additional arguments (required by HA interface).

        Raises:
            HomeAssistantError: If the stream cannot be disabled.
        """
        stream_type = self.entity_description.stream_type

        try:
            if stream_type == "ndi":
                await self.coordinator.client.async_set_ndi_enabled(False)
            else:
                await self.coordinator.client.async_set_stream_enabled(stream_type, False)
        except ZowietekApiError as err:
            _LOGGER.error("Failed to disable %s stream: %s", stream_type, err)
            raise HomeAssistantError(f"Failed to disable {stream_type} stream: {err}") from err

        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek switch entities.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for this integration instance.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    entities: list[ZowietekSwitch] = [
        ZowietekSwitch(coordinator, description) for description in SWITCH_DESCRIPTIONS
    ]

    async_add_entities(entities)
