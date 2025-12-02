"""Device triggers for the Zowietek integration.

This module provides device triggers for automations based on ZowieBox events
such as stream state changes and video input detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, HomeAssistant

# Event type fired on the event bus
EVENT_TYPE = f"{DOMAIN}_event"

# Available trigger types
TRIGGER_TYPES: set[str] = {
    "stream_started",
    "stream_stopped",
    "video_input_detected",
    "video_input_lost",
}

# Schema for validating trigger configuration
TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant,
    device_id: str,
) -> list[dict[str, str]]:
    """Return a list of triggers for a device.

    This function is called by Home Assistant to get the available triggers
    for a device. These triggers will appear in the automation UI.

    Args:
        hass: The Home Assistant instance.
        device_id: The device ID to get triggers for.

    Returns:
        A list of trigger dictionaries, each containing the trigger configuration.
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if device is None:
        return []

    # Check if this device belongs to our integration
    if not any(identifier[0] == DOMAIN for identifier in device.identifiers):
        return []

    triggers: list[dict[str, str]] = []

    for trigger_type in TRIGGER_TYPES:
        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: trigger_type,
            }
        )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger to listen for events.

    This function attaches the trigger to the event bus. When an event
    matching the trigger configuration is fired, the action is executed.

    Args:
        hass: The Home Assistant instance.
        config: The trigger configuration from the automation.
        action: The action to execute when the trigger fires.
        trigger_info: Additional information about the trigger.

    Returns:
        A callback function that detaches the trigger when called.
    """
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_TYPE,
            event_trigger.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                CONF_TYPE: config[CONF_TYPE],
            },
        }
    )

    return await event_trigger.async_attach_trigger(
        hass,
        event_config,
        action,
        trigger_info,
        platform_type="device",
    )
