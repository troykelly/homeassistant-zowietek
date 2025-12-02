"""The Zowietek integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from .const import DOMAIN
from .coordinator import ZowietekCoordinator
from .services import async_setup_services, async_unload_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.NUMBER,
]

type ZowietekConfigEntry = ConfigEntry[ZowietekCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
) -> bool:
    """Set up Zowietek from a config entry.

    This function initializes the coordinator, performs the first data refresh,
    and forwards setup to all entity platforms.

    The coordinator's async_config_entry_first_refresh() handles exceptions:
    - ConfigEntryAuthFailed: Triggers reauthentication flow
    - UpdateFailed: Converted to ConfigEntryNotReady for retry

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for this integration instance.

    Returns:
        True if setup was successful.

    Raises:
        ConfigEntryAuthFailed: If authentication fails during first refresh.
        ConfigEntryNotReady: If the device is unreachable during first refresh.
    """
    coordinator = ZowietekCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Register cleanup callback
    entry.async_on_unload(coordinator.client.close)

    # Register services if this is the first entry
    if not _async_has_other_entries(hass, entry):
        await async_setup_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ZowietekConfigEntry,
) -> bool:
    """Unload a config entry.

    This function unloads all entity platforms. The client session cleanup
    is handled by the on_unload callback registered during setup.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry to unload.

    Returns:
        True if unload was successful.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Unload services if this is the last entry
    if unload_ok and not _async_has_other_entries(hass, entry):
        await async_unload_services(hass)

    return unload_ok


def _async_has_other_entries(
    hass: HomeAssistant,
    current_entry: ZowietekConfigEntry,
) -> bool:
    """Check if there are other loaded config entries for this domain.

    Args:
        hass: The Home Assistant instance.
        current_entry: The current config entry to exclude.

    Returns:
        True if there are other loaded entries, False otherwise.
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    return any(
        entry.entry_id != current_entry.entry_id and entry.state.recoverable for entry in entries
    )
