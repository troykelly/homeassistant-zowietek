"""Switch platform for Zowietek integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import ZowietekConfigEntry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


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
    # Switch entities will be implemented in a future issue
