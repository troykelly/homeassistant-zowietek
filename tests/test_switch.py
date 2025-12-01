"""Tests for the Zowietek switch entities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek.const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test ZowieBox",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
        unique_id="zowiebox-test-12345",
        version=1,
    )


@pytest.fixture
def mock_device_info() -> dict[str, str]:
    """Return mock device info response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "devicesn": "zowiebox-test-12345",
        "devicename": "ZowieBox-Test",
        "softver": "1.2.3",
        "hardver": "2.0",
        "mac": "00:11:22:33:44:55",
        "model": "ZowieBox-4K",
        "uptime": "123456",
    }


@pytest.fixture
def mock_video_info() -> dict[str, str | int]:
    """Return mock video info response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "enc_type": "h264",
        "enc_bitrate": 8000,
        "enc_resolution": "1920x1080",
        "enc_framerate": 60,
        "mode": "encoder",
    }


@pytest.fixture
def mock_input_signal() -> dict[str, str | int]:
    """Return mock input signal response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "signal": 1,
        "width": 1920,
        "height": 1080,
        "fps": 60,
    }


@pytest.fixture
def mock_output_info() -> dict[str, str | int]:
    """Return mock output info response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "format": "1080p60",
        "loop_out_switch": 1,
    }


@pytest.fixture
def mock_stream_publish_info() -> dict[str, list[dict[str, str | int]]]:
    """Return mock stream publish info response with all streams enabled."""
    return {
        "publish": [
            {
                "type": "rtmp",
                "enable": 1,
                "url": "rtmp://example.com/live/stream",
            },
            {
                "type": "srt",
                "enable": 0,
                "url": "srt://example.com:1234",
            },
        ],
    }


@pytest.fixture
def mock_ndi_config() -> dict[str, str | int]:
    """Return mock NDI config response with NDI enabled."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "ndi_enable": 1,
        "ndi_name": "ZowieBox-Studio",
    }


@pytest.fixture
def mock_zowietek_client(
    mock_device_info: dict[str, str],
    mock_video_info: dict[str, str | int],
    mock_input_signal: dict[str, str | int],
    mock_output_info: dict[str, str | int],
    mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
    mock_ndi_config: dict[str, str | int],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for switch testing."""
    with patch(
        "custom_components.zowietek.coordinator.ZowietekClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_get_device_info = AsyncMock(return_value=mock_device_info)
        client.async_get_video_info = AsyncMock(return_value=mock_video_info)
        client.async_get_input_signal = AsyncMock(return_value=mock_input_signal)
        client.async_get_output_info = AsyncMock(return_value=mock_output_info)
        client.async_get_stream_publish_info = AsyncMock(return_value=mock_stream_publish_info)
        client.async_get_ndi_config = AsyncMock(return_value=mock_ndi_config)
        client.async_set_ndi_enabled = AsyncMock()
        client.async_set_stream_enabled = AsyncMock()
        client.close = AsyncMock()
        client.host = "http://192.168.1.100"
        yield client


async def _setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Set up the integration for testing."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


class TestSwitchDescriptions:
    """Tests for switch entity descriptions."""

    def test_switch_descriptions_defined(self) -> None:
        """Test that switch descriptions are defined."""
        from custom_components.zowietek.switch import SWITCH_DESCRIPTIONS

        assert SWITCH_DESCRIPTIONS is not None
        assert len(SWITCH_DESCRIPTIONS) == 3

    def test_ndi_stream_description(self) -> None:
        """Test NDI stream switch description."""
        from custom_components.zowietek.switch import SWITCH_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}
        assert "ndi_stream" in descriptions

        desc = descriptions["ndi_stream"]
        assert desc.translation_key == "ndi_stream"
        assert desc.icon == "mdi:broadcast"

    def test_rtmp_stream_description(self) -> None:
        """Test RTMP stream switch description."""
        from custom_components.zowietek.switch import SWITCH_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}
        assert "rtmp_stream" in descriptions

        desc = descriptions["rtmp_stream"]
        assert desc.translation_key == "rtmp_stream"
        assert desc.icon == "mdi:upload-network"

    def test_srt_stream_description(self) -> None:
        """Test SRT stream switch description."""
        from custom_components.zowietek.switch import SWITCH_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}
        assert "srt_stream" in descriptions

        desc = descriptions["srt_stream"]
        assert desc.translation_key == "srt_stream"
        assert desc.icon == "mdi:lan-connect"


class TestZowietekSwitchInit:
    """Tests for ZowietekSwitch initialization."""

    async def test_switch_inherits_from_zowietek_entity(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test ZowietekSwitch inherits from ZowietekEntity."""
        from custom_components.zowietek.entity import ZowietekEntity
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        description = SWITCH_DESCRIPTIONS[0]
        switch = ZowietekSwitch(coordinator, description)

        assert isinstance(switch, ZowietekEntity)

    async def test_switch_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch unique_id follows format {unique_id}_{key}."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        assert switch.unique_id == "zowiebox-test-12345_ndi_stream"

    async def test_switch_entity_description_set(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch has entity_description attribute set."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        assert switch.entity_description == descriptions["rtmp_stream"]


class TestZowietekSwitchState:
    """Tests for ZowietekSwitch is_on property."""

    async def test_ndi_stream_is_on_when_enabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI stream switch returns True when NDI is enabled."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        # NDI is enabled (ndi_enable: 1) in mock_ndi_config
        assert switch.is_on is True

    async def test_ndi_stream_is_off_when_disabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI stream switch returns False when NDI is disabled."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Modify mock to return disabled NDI
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "ndi_enable": 0,
            "ndi_name": "ZowieBox-Studio",
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        assert switch.is_on is False

    async def test_rtmp_stream_is_on_when_enabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test RTMP stream switch returns True when RTMP is enabled."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        # RTMP is enabled (enable: 1) in mock_stream_publish_info
        assert switch.is_on is True

    async def test_rtmp_stream_is_off_when_disabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test RTMP stream switch returns False when RTMP is disabled."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Modify mock to return disabled RTMP
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {
                    "type": "rtmp",
                    "enable": 0,
                    "url": "rtmp://example.com/live/stream",
                },
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        assert switch.is_on is False

    async def test_srt_stream_is_off_when_disabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test SRT stream switch returns False when SRT is disabled."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["srt_stream"])

        # SRT is disabled (enable: 0) in mock_stream_publish_info
        assert switch.is_on is False

    async def test_srt_stream_is_on_when_enabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test SRT stream switch returns True when SRT is enabled."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Modify mock to return enabled SRT
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {
                    "type": "srt",
                    "enable": 1,
                    "url": "srt://example.com:1234",
                },
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["srt_stream"])

        assert switch.is_on is True

    async def test_stream_not_in_publish_list_returns_false(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch returns False when stream type not in publish list."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Modify mock to return empty publish list
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        assert switch.is_on is False


class TestZowietekSwitchActions:
    """Tests for ZowietekSwitch turn_on and turn_off methods."""

    async def test_ndi_turn_on_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test turning on NDI switch calls the API."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        await switch.async_turn_on()

        mock_zowietek_client.async_set_ndi_enabled.assert_called_once_with(True)

    async def test_ndi_turn_off_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test turning off NDI switch calls the API."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        await switch.async_turn_off()

        mock_zowietek_client.async_set_ndi_enabled.assert_called_once_with(False)

    async def test_rtmp_turn_on_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test turning on RTMP switch calls the API."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        await switch.async_turn_on()

        mock_zowietek_client.async_set_stream_enabled.assert_called_once_with("rtmp", True)

    async def test_rtmp_turn_off_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test turning off RTMP switch calls the API."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        await switch.async_turn_off()

        mock_zowietek_client.async_set_stream_enabled.assert_called_once_with("rtmp", False)

    async def test_srt_turn_on_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test turning on SRT switch calls the API."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["srt_stream"])

        await switch.async_turn_on()

        mock_zowietek_client.async_set_stream_enabled.assert_called_once_with("srt", True)

    async def test_srt_turn_off_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test turning off SRT switch calls the API."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["srt_stream"])

        await switch.async_turn_off()

        mock_zowietek_client.async_set_stream_enabled.assert_called_once_with("srt", False)

    async def test_turn_on_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test turning on switch requests coordinator refresh."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        await switch.async_turn_on()

        coordinator.async_request_refresh.assert_called_once()

    async def test_turn_off_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test turning off switch requests coordinator refresh."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        await switch.async_turn_off()

        coordinator.async_request_refresh.assert_called_once()


class TestSwitchSetup:
    """Tests for switch platform setup."""

    async def test_async_setup_entry_creates_switches(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all switch entities."""
        from custom_components.zowietek.switch import SWITCH_DESCRIPTIONS

        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)

        switch_entries = [e for e in entries if e.domain == "switch"]
        assert len(switch_entries) == len(SWITCH_DESCRIPTIONS)

    async def test_switch_entities_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch entities are registered in entity registry."""
        from custom_components.zowietek.switch import SWITCH_DESCRIPTIONS

        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        for description in SWITCH_DESCRIPTIONS:
            entity_id = f"switch.zowiebox_test_{description.key}"
            entry = entity_registry.async_get(entity_id)
            assert entry is not None, f"Switch {entity_id} not registered"

    async def test_switch_states_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch states are available in Home Assistant."""
        await _setup_integration(hass, mock_config_entry)

        # Check NDI stream state (should be on)
        state = hass.states.get("switch.zowiebox_test_ndi_stream")
        assert state is not None
        assert state.state == STATE_ON

        # Check RTMP stream state (should be on)
        state = hass.states.get("switch.zowiebox_test_rtmp_stream")
        assert state is not None
        assert state.state == STATE_ON

        # Check SRT stream state (should be off)
        state = hass.states.get("switch.zowiebox_test_srt_stream")
        assert state is not None
        assert state.state == STATE_OFF


class TestSwitchAvailability:
    """Tests for switch availability."""

    async def test_switch_available_when_coordinator_has_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch is available when coordinator has data."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        assert switch.available is True

    async def test_switch_unavailable_when_coordinator_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch is unavailable when coordinator update fails."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.last_update_success = False

        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}
        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        assert switch.available is False


class TestSwitchDeviceInfo:
    """Tests for switch device info."""

    async def test_switch_has_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch has device_info property from base entity."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])
        device_info = switch.device_info

        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "zowiebox-test-12345")}
        assert device_info["manufacturer"] == "Zowietek"


class TestSwitchEdgeCases:
    """Tests for edge cases in switch behavior."""

    async def test_coordinator_data_none_returns_false(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch returns False when coordinator data is None."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        # Manually set coordinator.data to None
        coordinator.data = None

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        assert switch.is_on is False

    async def test_stream_data_missing_returns_false(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch returns False when stream data is missing."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Return empty stream data
        mock_zowietek_client.async_get_stream_publish_info.return_value = {"publish": []}
        mock_zowietek_client.async_get_ndi_config.return_value = {}

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        assert switch.is_on is False

    async def test_ndi_enable_as_string_one(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI switch handles string '1' for enabled."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Return string instead of int
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "ndi_enable": "1",
            "ndi_name": "ZowieBox-Studio",
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        assert switch.is_on is True

    async def test_ndi_enable_as_string_zero(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI switch handles string '0' for disabled."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Return string instead of int
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "ndi_enable": "0",
            "ndi_name": "ZowieBox-Studio",
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["ndi_stream"])

        assert switch.is_on is False

    async def test_publish_enable_as_string(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test stream switch handles string enable values."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Return string instead of int for enable
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {
                    "type": "rtmp",
                    "enable": "1",
                    "url": "rtmp://example.com/live/stream",
                },
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        assert switch.is_on is True

    async def test_publish_list_not_list_returns_false(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch returns False when publish is not a list."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Return non-list value for publish
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": "not_a_list",
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        assert switch.is_on is False

    async def test_publish_entry_not_dict_skipped(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch skips non-dict entries in publish list."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Return list with non-dict entry followed by valid entry
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                "not_a_dict",
                {
                    "type": "rtmp",
                    "enable": 1,
                    "url": "rtmp://example.com/live/stream",
                },
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        # Should skip the non-dict entry and find the valid one
        assert switch.is_on is True

    async def test_publish_entry_enable_none_returns_false(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test switch returns False when enable key is None."""
        from custom_components.zowietek.switch import (
            SWITCH_DESCRIPTIONS,
            ZowietekSwitch,
        )

        # Return entry without enable key
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {
                    "type": "rtmp",
                    # enable key missing
                    "url": "rtmp://example.com/live/stream",
                },
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SWITCH_DESCRIPTIONS}

        switch = ZowietekSwitch(coordinator, descriptions["rtmp_stream"])

        assert switch.is_on is False
