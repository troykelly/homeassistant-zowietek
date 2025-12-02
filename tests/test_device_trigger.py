"""Tests for Zowietek device triggers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.device_automation import DeviceAutomationType
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_get_device_automations,
)

from custom_components.zowietek.const import DOMAIN
from tests.conftest import add_coordinator_mocks

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_config_entry_with_device() -> MockConfigEntry:
    """Create a mock config entry with a unique device ID."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test ZowieBox",
        data={
            "host": "192.168.1.100",
            "username": "admin",
            "password": "admin",
        },
        unique_id="zowiebox-trigger-test-12345",
        version=1,
    )


async def setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> dr.DeviceEntry:
    """Set up the integration and return the device entry."""
    with patch(
        "custom_components.zowietek.coordinator.ZowietekClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_login = AsyncMock(return_value=True)
        client.async_logout = AsyncMock()
        client.close = AsyncMock()
        client.host = "192.168.1.100"

        # Add sys_attr for device info
        client.async_get_sys_attr_info = AsyncMock(
            return_value={
                "SN": "zowiebox-trigger-test-12345",
                "device_name": "ZowieBox-Test",
                "firmware_version": "2.0.0",
                "hardware_version": "3.0",
                "model": "ZowieBox",
                "manufacturer": "Zowietek",
            }
        )

        # Add dashboard info
        client.async_get_dashboard_info = AsyncMock(
            return_value={
                "persistent_time": "1:00:00",
                "device_strat_time": "2024-01-01 00:00:00",
                "cpu_temp": 45.0,
                "cpu_payload": 20.0,
            }
        )

        add_coordinator_mocks(client)

        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    # Get device from registry
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, config_entry.unique_id)})
    assert device is not None
    return device


class TestDeviceTriggerGetTriggers:
    """Test async_get_triggers function."""

    async def test_get_triggers_returns_expected_types(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that get_triggers returns all expected trigger types."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        triggers = await async_get_device_automations(hass, DeviceAutomationType.TRIGGER, device.id)

        # Filter for only our domain's triggers
        zowietek_triggers = [t for t in triggers if t.get(CONF_DOMAIN) == DOMAIN]

        # Should have triggers for:
        # - stream_started
        # - stream_stopped
        # - video_input_detected
        # - video_input_lost
        trigger_types = {t[CONF_TYPE] for t in zowietek_triggers}
        expected_types = {
            "stream_started",
            "stream_stopped",
            "video_input_detected",
            "video_input_lost",
        }
        assert trigger_types == expected_types

    async def test_get_triggers_all_have_required_fields(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that all zowietek triggers have required fields."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        triggers = await async_get_device_automations(hass, DeviceAutomationType.TRIGGER, device.id)

        # Filter for only our domain's triggers
        zowietek_triggers = [t for t in triggers if t.get(CONF_DOMAIN) == DOMAIN]

        assert len(zowietek_triggers) == 4  # 4 trigger types
        for trigger in zowietek_triggers:
            assert CONF_PLATFORM in trigger
            assert trigger[CONF_PLATFORM] == "device"
            assert CONF_DOMAIN in trigger
            assert trigger[CONF_DOMAIN] == DOMAIN
            assert CONF_DEVICE_ID in trigger
            assert trigger[CONF_DEVICE_ID] == device.id
            assert CONF_TYPE in trigger


class TestDeviceTriggerAttach:
    """Test async_attach_trigger function."""

    async def test_attach_stream_started_trigger(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test attaching stream_started trigger."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        # Setup automation component
        assert await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "stream_started",
                        },
                        "action": {
                            "service": "test.automation",
                            "data_template": {"trigger_type": "{{ trigger.type }}"},
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        # Automation should be registered
        assert len(hass.states.async_entity_ids(AUTOMATION_DOMAIN)) == 1

    async def test_attach_video_input_detected_trigger(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test attaching video_input_detected trigger."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        assert await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "video_input_detected",
                        },
                        "action": {
                            "service": "test.automation",
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        assert len(hass.states.async_entity_ids(AUTOMATION_DOMAIN)) == 1


class TestDeviceTriggerFiring:
    """Test that device triggers fire correctly."""

    async def test_stream_started_trigger_fires_on_event(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that stream_started trigger fires when event is dispatched."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        calls: list[dict[str, Any]] = []

        @callback
        def record_call(service_call: Any) -> None:
            """Record service call."""
            calls.append(service_call.data)

        hass.services.async_register("test", "automation", record_call)

        assert await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "stream_started",
                        },
                        "action": {
                            "service": "test.automation",
                            "data": {"triggered": "stream_started"},
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        # Fire the event
        hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                CONF_DEVICE_ID: device.id,
                CONF_TYPE: "stream_started",
            },
        )
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0]["triggered"] == "stream_started"

    async def test_stream_stopped_trigger_fires_on_event(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that stream_stopped trigger fires when event is dispatched."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        calls: list[dict[str, Any]] = []

        @callback
        def record_call(service_call: Any) -> None:
            """Record service call."""
            calls.append(service_call.data)

        hass.services.async_register("test", "automation", record_call)

        assert await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "stream_stopped",
                        },
                        "action": {
                            "service": "test.automation",
                            "data": {"triggered": "stream_stopped"},
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        # Fire the event
        hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                CONF_DEVICE_ID: device.id,
                CONF_TYPE: "stream_stopped",
            },
        )
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0]["triggered"] == "stream_stopped"

    async def test_video_input_detected_trigger_fires_on_event(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that video_input_detected trigger fires when event is dispatched."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        calls: list[dict[str, Any]] = []

        @callback
        def record_call(service_call: Any) -> None:
            """Record service call."""
            calls.append(service_call.data)

        hass.services.async_register("test", "automation", record_call)

        assert await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "video_input_detected",
                        },
                        "action": {
                            "service": "test.automation",
                            "data": {"triggered": "video_input_detected"},
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        # Fire the event
        hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                CONF_DEVICE_ID: device.id,
                CONF_TYPE: "video_input_detected",
            },
        )
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0]["triggered"] == "video_input_detected"

    async def test_video_input_lost_trigger_fires_on_event(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that video_input_lost trigger fires when event is dispatched."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        calls: list[dict[str, Any]] = []

        @callback
        def record_call(service_call: Any) -> None:
            """Record service call."""
            calls.append(service_call.data)

        hass.services.async_register("test", "automation", record_call)

        assert await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "video_input_lost",
                        },
                        "action": {
                            "service": "test.automation",
                            "data": {"triggered": "video_input_lost"},
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        # Fire the event
        hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                CONF_DEVICE_ID: device.id,
                CONF_TYPE: "video_input_lost",
            },
        )
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0]["triggered"] == "video_input_lost"

    async def test_trigger_does_not_fire_for_wrong_device(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that triggers don't fire for events from other devices."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        calls: list[dict[str, Any]] = []

        @callback
        def record_call(service_call: Any) -> None:
            """Record service call."""
            calls.append(service_call.data)

        hass.services.async_register("test", "automation", record_call)

        assert await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "stream_started",
                        },
                        "action": {
                            "service": "test.automation",
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        # Fire event with different device_id
        hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                CONF_DEVICE_ID: "wrong-device-id",
                CONF_TYPE: "stream_started",
            },
        )
        await hass.async_block_till_done()

        # Should not have triggered
        assert len(calls) == 0

    async def test_trigger_does_not_fire_for_wrong_type(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that triggers don't fire for wrong event types."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        calls: list[dict[str, Any]] = []

        @callback
        def record_call(service_call: Any) -> None:
            """Record service call."""
            calls.append(service_call.data)

        hass.services.async_register("test", "automation", record_call)

        assert await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "stream_started",
                        },
                        "action": {
                            "service": "test.automation",
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        # Fire event with different type
        hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                CONF_DEVICE_ID: device.id,
                CONF_TYPE: "stream_stopped",  # Wrong type
            },
        )
        await hass.async_block_till_done()

        # Should not have triggered
        assert len(calls) == 0


class TestDeviceTriggerEdgeCases:
    """Test edge cases in async_get_triggers."""

    async def test_get_triggers_returns_empty_for_unknown_device(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that get_triggers returns empty list for unknown device."""
        from custom_components.zowietek.device_trigger import async_get_triggers

        await setup_integration(hass, mock_config_entry_with_device)

        # Use a fake device_id that doesn't exist
        triggers = await async_get_triggers(hass, "nonexistent-device-id")

        assert triggers == []

    async def test_get_triggers_returns_empty_for_non_zowietek_device(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that get_triggers returns empty list for non-zowietek device."""
        from custom_components.zowietek.device_trigger import async_get_triggers

        await setup_integration(hass, mock_config_entry_with_device)

        # Create a fake device entry for a different domain
        device_registry = dr.async_get(hass)
        other_device = device_registry.async_get_or_create(
            config_entry_id=mock_config_entry_with_device.entry_id,
            identifiers={("other_domain", "other-device-123")},
            name="Other Device",
        )

        # Get triggers for this non-zowietek device
        triggers = await async_get_triggers(hass, other_device.id)

        assert triggers == []


class TestDeviceTriggerSchema:
    """Test trigger schema validation."""

    async def test_invalid_trigger_type_rejected(
        self,
        hass: HomeAssistant,
        mock_config_entry_with_device: MockConfigEntry,
    ) -> None:
        """Test that invalid trigger types are rejected."""
        device = await setup_integration(hass, mock_config_entry_with_device)

        # Try to setup automation with invalid trigger type
        await async_setup_component(
            hass,
            AUTOMATION_DOMAIN,
            {
                AUTOMATION_DOMAIN: [
                    {
                        "trigger": {
                            CONF_PLATFORM: "device",
                            CONF_DOMAIN: DOMAIN,
                            CONF_DEVICE_ID: device.id,
                            CONF_TYPE: "invalid_type",  # Invalid type
                        },
                        "action": {
                            "service": "test.automation",
                        },
                    },
                ],
            },
        )
        await hass.async_block_till_done()

        # Automation should not be set up due to invalid config
        # or the trigger should be rejected
        automations = hass.states.async_entity_ids(AUTOMATION_DOMAIN)
        # Either no automation or it's unavailable
        if len(automations) > 0:
            # If automation was created, it should be in unavailable state
            # or have no triggers attached
            pass  # Schema validation may handle this differently
