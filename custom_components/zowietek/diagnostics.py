"""Diagnostics support for Zowietek integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from .coordinator import ZowietekCoordinator

# Keys to redact from diagnostics output for security/privacy
TO_REDACT: set[str] = {
    "password",
    "psw",
    "SN",
    "serial_number",
    "mac_address",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry[ZowietekCoordinator],
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    This function is called when a user downloads diagnostics for this
    integration from the device page. It returns a dictionary containing
    configuration and device data with sensitive information redacted.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry to get diagnostics for.

    Returns:
        Dictionary containing redacted diagnostics data suitable for
        sharing in bug reports and support requests.
    """
    coordinator: ZowietekCoordinator = entry.runtime_data

    # Build device data section if coordinator has data
    device_data: dict[str, Any] | None = None
    if coordinator.data is not None:
        device_data = async_redact_data(
            {
                "system": dict(coordinator.data.system),
                "video": dict(coordinator.data.video),
                "audio": dict(coordinator.data.audio),
                "stream": dict(coordinator.data.stream),
                "network": dict(coordinator.data.network),
                "dashboard": dict(coordinator.data.dashboard),
            },
            TO_REDACT,
        )

    return {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "device_data": device_data,
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "consecutive_failures": coordinator.consecutive_failures,
        },
    }
