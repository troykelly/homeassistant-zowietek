"""Button platform for Zowietek integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from . import ZowietekConfigEntry
from .coordinator import ZowietekCoordinator
from .entity import ZowietekEntity
from .exceptions import ZowietekError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


BUTTON_DESCRIPTIONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="reboot",
        translation_key="reboot",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
    ),
    ButtonEntityDescription(
        key="refresh",
        translation_key="refresh",
        icon="mdi:refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


class ZowietekButton(ZowietekEntity, ButtonEntity):
    """Zowietek button entity for device actions.

    Represents a button that triggers device actions like reboot
    or force refresh on the ZowieBox device.
    """

    entity_description: ButtonEntityDescription

    def __init__(
        self,
        coordinator: ZowietekCoordinator,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button.

        Args:
            coordinator: The data update coordinator for this device.
            description: Entity description for this button.
        """
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Handle button press.

        Executes the action associated with this button.

        Raises:
            HomeAssistantError: If the action fails.
        """
        key = self.entity_description.key

        if key == "reboot":
            try:
                await self.coordinator.client.async_reboot()
            except ZowietekError as err:
                _LOGGER.error("Failed to reboot device: %s", err)
                raise HomeAssistantError(f"Failed to reboot device: {err}") from err
        elif key == "refresh":
            await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zowietek button entities.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for this integration instance.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data

    entities: list[ZowietekButton] = [
        ZowietekButton(coordinator, description) for description in BUTTON_DESCRIPTIONS
    ]

    async_add_entities(entities)
