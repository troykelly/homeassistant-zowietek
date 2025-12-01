"""Tests for the Zowietek button entities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    EntityCategory,
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
def mock_input_signal() -> dict[str, str | int]:
    """Return mock input signal response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "hdmi_signal": 1,
        "audio_signal": 48000,
        "width": 1920,
        "height": 1080,
        "framerate": 60,
        "desc": "1080p60",
    }


@pytest.fixture
def mock_venc_info() -> dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]]:
    """Return mock video encoder info response."""
    return {
        "venc": [
            {
                "venc_chnid": 0,
                "codec": {
                    "selected_id": 0,
                    "codec_list": ["H.264", "H.265", "MJPEG"],
                },
                "bitrate": 12000000,
                "width": 1920,
                "height": 1080,
                "framerate": 60,
                "desc": "main",
            },
        ],
    }


@pytest.fixture
def mock_audio_info() -> dict[str, str | int | dict[str, str | int | list[str]]]:
    """Return mock audio info response."""
    return {
        "switch": 1,
        "ai_type": {
            "selected_id": 0,
            "ai_type_list": ["LINE IN", "Internal MIC", "HDMI IN", "USB IN"],
        },
        "volume": 100,
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
    """Return mock stream publish info response."""
    return {
        "publish": [
            {
                "type": "rtmp",
                "switch": 1,
                "url": "rtmp://example.com/live/stream",
            },
        ],
    }


@pytest.fixture
def mock_ndi_config() -> dict[str, str | int]:
    """Return mock NDI config response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "activate": 1,
        "switch": 1,
        "mode_id": 1,
        "machinename": "ZowieBox-Studio",
        "groups": "Public",
    }


@pytest.fixture
def mock_sys_attr() -> dict[str, str]:
    """Return mock system attributes response."""
    return {
        "SN": "zowiebox-test-12345",
        "device_name": "ZowieBox-Studio",
        "firmware_version": "1.2.3",
        "hardware_version": "2.0",
        "model": "ZowieBox-4K",
        "manufacturer": "Zowietek",
        "ndi_version": "5.0",
    }


@pytest.fixture
def mock_dashboard_info() -> dict[str, str | int | float | dict[str, int]]:
    """Return mock dashboard info response."""
    return {
        "persistent_time": "02:30:15",
        "device_strat_time": "2025-11-30 10:00:00",
        "cpu_temp": 45.5,
        "cpu_payload": 25.0,
        "memory_info": {
            "used": 512,
            "total": 1024,
        },
    }


@pytest.fixture
def mock_zowietek_client(
    mock_input_signal: dict[str, str | int],
    mock_output_info: dict[str, str | int],
    mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
    mock_ndi_config: dict[str, str | int],
    mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
    mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
    mock_sys_attr: dict[str, str],
    mock_dashboard_info: dict[str, str | int | float | dict[str, int]],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for button testing."""
    with patch(
        "custom_components.zowietek.coordinator.ZowietekClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_get_input_signal = AsyncMock(return_value=mock_input_signal)
        client.async_get_output_info = AsyncMock(return_value=mock_output_info)
        client.async_get_stream_publish_info = AsyncMock(return_value=mock_stream_publish_info)
        client.async_get_ndi_config = AsyncMock(return_value=mock_ndi_config)
        client.async_get_venc_info = AsyncMock(return_value=mock_venc_info)
        client.async_get_audio_info = AsyncMock(return_value=mock_audio_info)
        client.async_get_sys_attr_info = AsyncMock(return_value=mock_sys_attr)
        client.async_get_dashboard_info = AsyncMock(return_value=mock_dashboard_info)
        client.async_reboot = AsyncMock()
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


class TestButtonDescriptions:
    """Tests for button entity descriptions."""

    def test_button_descriptions_defined(self) -> None:
        """Test that button descriptions are defined."""
        from custom_components.zowietek.button import BUTTON_DESCRIPTIONS

        assert BUTTON_DESCRIPTIONS is not None
        assert len(BUTTON_DESCRIPTIONS) == 2

    def test_reboot_button_description(self) -> None:
        """Test reboot button description."""
        from custom_components.zowietek.button import BUTTON_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}
        assert "reboot" in descriptions

        desc = descriptions["reboot"]
        assert desc.translation_key == "reboot"
        assert desc.device_class == ButtonDeviceClass.RESTART
        assert desc.entity_category == EntityCategory.CONFIG

    def test_refresh_button_description(self) -> None:
        """Test refresh button description."""
        from custom_components.zowietek.button import BUTTON_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}
        assert "refresh" in descriptions

        desc = descriptions["refresh"]
        assert desc.translation_key == "refresh"
        assert desc.icon == "mdi:refresh"
        assert desc.entity_category == EntityCategory.DIAGNOSTIC


class TestZowietekButtonInit:
    """Tests for ZowietekButton initialization."""

    async def test_button_inherits_from_zowietek_entity(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test ZowietekButton inherits from ZowietekEntity."""
        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )
        from custom_components.zowietek.entity import ZowietekEntity

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        description = BUTTON_DESCRIPTIONS[0]
        button = ZowietekButton(coordinator, description)

        assert isinstance(button, ZowietekEntity)

    async def test_button_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test button unique_id follows format {unique_id}_{key}."""
        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}

        button = ZowietekButton(coordinator, descriptions["reboot"])

        assert button.unique_id == "zowiebox-test-12345_reboot"

    async def test_button_entity_description_set(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test button has entity_description attribute set."""
        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}

        button = ZowietekButton(coordinator, descriptions["refresh"])

        assert button.entity_description == descriptions["refresh"]


class TestZowietekButtonPress:
    """Tests for ZowietekButton async_press method."""

    async def test_reboot_button_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test pressing reboot button calls the API."""
        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}

        button = ZowietekButton(coordinator, descriptions["reboot"])

        await button.async_press()

        mock_zowietek_client.async_reboot.assert_called_once()

    async def test_refresh_button_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test pressing refresh button requests coordinator refresh."""
        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}

        button = ZowietekButton(coordinator, descriptions["refresh"])

        await button.async_press()

        coordinator.async_request_refresh.assert_called_once()

    async def test_reboot_button_api_error_raises_ha_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test reboot button raises HomeAssistantError when API fails."""
        from homeassistant.exceptions import HomeAssistantError

        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )
        from custom_components.zowietek.exceptions import ZowietekApiError

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}

        # Make API call raise an error
        mock_zowietek_client.async_reboot.side_effect = ZowietekApiError(
            "Device not responding", "00000"
        )

        button = ZowietekButton(coordinator, descriptions["reboot"])

        with pytest.raises(HomeAssistantError) as exc_info:
            await button.async_press()

        assert "Failed to reboot device" in str(exc_info.value)


class TestButtonSetup:
    """Tests for button platform setup."""

    async def test_async_setup_entry_creates_buttons(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all button entities."""
        from custom_components.zowietek.button import BUTTON_DESCRIPTIONS

        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)

        button_entries = [e for e in entries if e.domain == BUTTON_DOMAIN]
        assert len(button_entries) == len(BUTTON_DESCRIPTIONS)

    async def test_button_entities_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test button entities are registered in entity registry."""
        from custom_components.zowietek.button import BUTTON_DESCRIPTIONS

        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        for description in BUTTON_DESCRIPTIONS:
            entity_id = f"button.zowiebox_studio_{description.key}"
            entry = entity_registry.async_get(entity_id)
            assert entry is not None, f"Button {entity_id} not registered"

    async def test_button_states_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test button states are available in Home Assistant."""
        await _setup_integration(hass, mock_config_entry)

        # Check reboot button state
        state = hass.states.get("button.zowiebox_studio_reboot")
        assert state is not None

        # Check refresh button state
        state = hass.states.get("button.zowiebox_studio_refresh")
        assert state is not None


class TestButtonAvailability:
    """Tests for button availability."""

    async def test_button_available_when_coordinator_has_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test button is available when coordinator has data."""
        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}

        button = ZowietekButton(coordinator, descriptions["reboot"])

        assert button.available is True

    async def test_button_unavailable_when_coordinator_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test button is unavailable when coordinator update fails."""
        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.last_update_success = False

        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}
        button = ZowietekButton(coordinator, descriptions["reboot"])

        assert button.available is False


class TestButtonDeviceInfo:
    """Tests for button device info."""

    async def test_button_has_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test button has device_info property from base entity."""
        from custom_components.zowietek.button import (
            BUTTON_DESCRIPTIONS,
            ZowietekButton,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BUTTON_DESCRIPTIONS}

        button = ZowietekButton(coordinator, descriptions["reboot"])
        device_info = button.device_info

        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "zowiebox-test-12345")}
        assert device_info["manufacturer"] == "Zowietek"


class TestButtonHaService:
    """Tests for button Home Assistant service calls."""

    async def test_reboot_via_service_call(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test reboot button can be pressed via HA service call."""
        await _setup_integration(hass, mock_config_entry)

        # Call the button press service
        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {"entity_id": "button.zowiebox_studio_reboot"},
            blocking=True,
        )

        mock_zowietek_client.async_reboot.assert_called_once()

    async def test_refresh_via_service_call(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test refresh button can be pressed via HA service call."""
        await _setup_integration(hass, mock_config_entry)

        # Reset the mock to track only the refresh call
        mock_zowietek_client.async_get_input_signal.reset_mock()

        # Call the button press service
        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {"entity_id": "button.zowiebox_studio_refresh"},
            blocking=True,
        )

        # The refresh button should trigger coordinator refresh which fetches data
        # Since we're using async_request_refresh, we just verify no exceptions
        # The coordinator will call the API methods again
        await hass.async_block_till_done()
