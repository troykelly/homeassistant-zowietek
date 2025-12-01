"""Tests for the Zowietek select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
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
        "devicename": "ZowieBox-Studio",
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
            {
                "venc_chnid": 1,
                "codec": {
                    "selected_id": 0,
                    "codec_list": ["H.264", "H.265"],
                },
                "bitrate": 1000000,
                "width": 1280,
                "height": 720,
                "framerate": 30,
                "desc": "sub",
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
def mock_output_info() -> dict[str, str | int | dict[str, int | list[str]]]:
    """Return mock output info response with format options."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "format": "1080p60",
        "format_list": {
            "selected_id": 2,
            "list": ["720p50", "720p60", "1080p50", "1080p60", "2160p30"],
        },
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
            {
                "type": "srt",
                "switch": 0,
                "url": "srt://example.com:1234",
            },
        ],
    }


@pytest.fixture
def mock_ndi_config() -> dict[str, str | int | dict[str, int | list[str]]]:
    """Return mock NDI config response with mode options."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "activate": 1,
        "switch": 1,
        "mode_id": 3,
        "mode": {
            "selected_id": 2,
            "mode_list": ["NDI|HX", "NDI|HX2", "NDI|HX3"],
        },
        "machinename": "ZowieBox-Studio",
        "groups": "Public",
    }


@pytest.fixture
def mock_sys_attr_info() -> dict[str, str]:
    """Return mock sys_attr info response."""
    return {
        "SN": "zowiebox-test-12345",
        "firmware_version": "1.2.3",
        "hardware_version": "2.0",
        "model": "ZowieBox",
        "manufacturer": "Zowietek",
        "device_name": "ZowieBox-Studio",
        "ndi_version": "5.0.0",
    }


@pytest.fixture
def mock_dashboard_info() -> dict[str, str | float | dict[str, int]]:
    """Return mock dashboard info response."""
    return {
        "persistent_time": "01:23:45",
        "device_strat_time": "2024-01-01 00:00:00",
        "cpu_temp": 45.5,
        "cpu_payload": 25.0,
        "memory_info": {
            "used": 256,
            "total": 512,
        },
    }


@pytest.fixture
def mock_zowietek_client(
    mock_device_info: dict[str, str],
    mock_video_info: dict[str, str | int],
    mock_input_signal: dict[str, str | int],
    mock_output_info: dict[str, str | int | dict[str, int | list[str]]],
    mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
    mock_ndi_config: dict[str, str | int | dict[str, int | list[str]]],
    mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
    mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
    mock_sys_attr_info: dict[str, str],
    mock_dashboard_info: dict[str, str | float | dict[str, int]],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for select testing."""
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
        client.async_get_venc_info = AsyncMock(return_value=mock_venc_info)
        client.async_get_audio_info = AsyncMock(return_value=mock_audio_info)
        client.async_get_sys_attr_info = AsyncMock(return_value=mock_sys_attr_info)
        client.async_get_dashboard_info = AsyncMock(return_value=mock_dashboard_info)
        # Write methods for select entities
        client.async_set_output_format = AsyncMock()
        client.async_set_encoder_codec = AsyncMock()
        client.async_set_ndi_mode = AsyncMock()
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


class TestSelectDescriptions:
    """Tests for select entity descriptions."""

    def test_select_descriptions_defined(self) -> None:
        """Test that select descriptions are defined."""
        from custom_components.zowietek.select import SELECT_DESCRIPTIONS

        assert SELECT_DESCRIPTIONS is not None
        assert len(SELECT_DESCRIPTIONS) >= 2  # At least encoder_type and output_format

    def test_encoder_type_description(self) -> None:
        """Test encoder type select description."""
        from custom_components.zowietek.select import SELECT_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}
        assert "encoder_type" in descriptions

        desc = descriptions["encoder_type"]
        assert desc.translation_key == "encoder_type"
        assert desc.icon == "mdi:video-box"

    def test_output_format_description(self) -> None:
        """Test output format select description."""
        from custom_components.zowietek.select import SELECT_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}
        assert "output_format" in descriptions

        desc = descriptions["output_format"]
        assert desc.translation_key == "output_format"
        assert desc.icon == "mdi:monitor"


class TestZowietekSelectInit:
    """Tests for ZowietekSelect initialization."""

    async def test_select_inherits_from_zowietek_entity(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test ZowietekSelect inherits from ZowietekEntity."""
        from custom_components.zowietek.entity import ZowietekEntity
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        description = SELECT_DESCRIPTIONS[0]
        select = ZowietekSelect(coordinator, description)

        assert isinstance(select, ZowietekEntity)

    async def test_select_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select unique_id follows format {unique_id}_{key}."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.unique_id == "zowiebox-test-12345_encoder_type"

    async def test_select_entity_description_set(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select has entity_description attribute set."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.entity_description == descriptions["encoder_type"]


class TestEncoderTypeSelect:
    """Tests for encoder type select entity."""

    async def test_encoder_type_current_option(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test encoder type select returns current codec."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        # Mock venc_info has codec.selected_id=0 which is "H.264"
        assert select.current_option == "H.264"

    async def test_encoder_type_options(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test encoder type select returns available codecs."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        # Mock venc_info has codec_list: ["H.264", "H.265", "MJPEG"]
        assert select.options == ["H.264", "H.265", "MJPEG"]

    async def test_encoder_type_select_option_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test selecting encoder type calls the API."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        await select.async_select_option("H.265")

        mock_zowietek_client.async_set_encoder_codec.assert_called_once_with(1)

    async def test_encoder_type_h264_selection(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test selecting H.264 encoder type."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        # Change initial selected codec to H.265
        mock_zowietek_client.async_get_venc_info.return_value = {
            "venc": [
                {
                    "venc_chnid": 0,
                    "codec": {
                        "selected_id": 1,
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

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        # Current should be H.265
        assert select.current_option == "H.265"

        await select.async_select_option("H.264")

        mock_zowietek_client.async_set_encoder_codec.assert_called_once_with(0)


class TestOutputFormatSelect:
    """Tests for output format select entity."""

    async def test_output_format_current_option(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test output format select returns current format."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["output_format"])

        # Mock output_info has format: "1080p60"
        assert select.current_option == "1080p60"

    async def test_output_format_options(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test output format select returns available formats."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["output_format"])

        # Mock output_info has format_list with list
        assert "1080p60" in select.options
        assert "2160p30" in select.options

    async def test_output_format_select_option_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test selecting output format calls the API."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["output_format"])

        await select.async_select_option("2160p30")

        mock_zowietek_client.async_set_output_format.assert_called_once_with("2160p30")


class TestSelectSetup:
    """Tests for select platform setup."""

    async def test_async_setup_entry_creates_selects(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all select entities."""
        from custom_components.zowietek.select import SELECT_DESCRIPTIONS

        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)

        select_entries = [e for e in entries if e.domain == "select"]
        assert len(select_entries) == len(SELECT_DESCRIPTIONS)

    async def test_select_entities_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select entities are registered in entity registry."""
        from custom_components.zowietek.select import SELECT_DESCRIPTIONS

        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        for description in SELECT_DESCRIPTIONS:
            entity_id = f"select.zowiebox_studio_{description.key}"
            entry = entity_registry.async_get(entity_id)
            assert entry is not None, f"Select {entity_id} not registered"

    async def test_select_states_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select states are available in Home Assistant."""
        await _setup_integration(hass, mock_config_entry)

        # Check encoder type state
        state = hass.states.get("select.zowiebox_studio_encoder_type")
        assert state is not None
        assert state.state == "H.264"

        # Check output format state
        state = hass.states.get("select.zowiebox_studio_output_format")
        assert state is not None
        assert state.state == "1080p60"


class TestSelectAvailability:
    """Tests for select availability."""

    async def test_select_available_when_coordinator_has_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select is available when coordinator has data."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.available is True

    async def test_select_unavailable_when_coordinator_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select is unavailable when coordinator update fails."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.last_update_success = False

        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}
        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.available is False


class TestSelectDeviceInfo:
    """Tests for select device info."""

    async def test_select_has_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select has device_info property from base entity."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])
        device_info = select.device_info

        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "zowiebox-test-12345")}
        assert device_info["manufacturer"] == "Zowietek"


class TestSelectEdgeCases:
    """Tests for edge cases in select behavior."""

    async def test_coordinator_data_none_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select returns None when coordinator data is None."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        # Manually set coordinator.data to None
        coordinator.data = None

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.current_option is None

    async def test_encoder_type_no_venc_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test encoder type handles missing venc data gracefully."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        # Return empty venc data
        mock_zowietek_client.async_get_venc_info.return_value = {"venc": []}

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.current_option is None
        assert select.options == []

    async def test_select_option_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test selecting option requests coordinator refresh."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        await select.async_select_option("H.265")

        coordinator.async_request_refresh.assert_called_once()

    async def test_select_option_api_error_raises_ha_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select_option raises HomeAssistantError when API fails."""
        from homeassistant.exceptions import HomeAssistantError

        from custom_components.zowietek.exceptions import ZowietekApiError
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        # Make API call raise an error
        mock_zowietek_client.async_set_encoder_codec.side_effect = ZowietekApiError(
            "Invalid codec", "00003"
        )

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        with pytest.raises(HomeAssistantError) as exc_info:
            await select.async_select_option("H.265")

        assert "Failed to set encoder_type" in str(exc_info.value)

    async def test_invalid_option_not_in_list(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test selecting invalid option raises error."""
        from homeassistant.exceptions import HomeAssistantError

        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        # Try to select option not in list
        with pytest.raises(HomeAssistantError) as exc_info:
            await select.async_select_option("INVALID_CODEC")

        assert "Invalid option" in str(exc_info.value)

    async def test_output_format_fallback_options(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test output format uses fallback options when format_list not available."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        # Remove format_list from output_info
        mock_zowietek_client.async_get_output_info.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "format": "1080p60",
            "loop_out_switch": 1,
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["output_format"])

        # Should use default fallback options
        assert len(select.options) > 0
        assert "1080p60" in select.options

    async def test_codec_selected_id_not_int_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test encoder type returns None when codec_selected_id is not int."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        # Manually set codec_selected_id to a non-int value in data
        coordinator.data.video["codec_selected_id"] = "invalid"

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.current_option is None

    async def test_codec_selected_id_out_of_bounds(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test encoder type returns None when codec_selected_id is out of bounds."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        # Return selected_id out of bounds
        mock_zowietek_client.async_get_venc_info.return_value = {
            "venc": [
                {
                    "venc_chnid": 0,
                    "codec": {
                        "selected_id": 99,  # Out of bounds
                        "codec_list": ["H.264", "H.265"],
                    },
                    "desc": "main",
                },
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.current_option is None

    async def test_output_format_none_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test output format returns None when format not in data."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        # Manually remove output_format from data
        del coordinator.data.video["output_format"]

        select = ZowietekSelect(coordinator, descriptions["output_format"])

        assert select.current_option is None

    async def test_set_encoder_codec_not_found_raises_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setting encoder type raises error when codec not in list."""
        from custom_components.zowietek.exceptions import ZowietekApiError
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        # Test the internal _set_encoder_type directly with invalid codec
        with pytest.raises(ZowietekApiError) as exc_info:
            await select._set_encoder_type("UNKNOWN_CODEC")

        assert "not found" in str(exc_info.value)

    async def test_set_encoder_codec_list_not_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setting encoder type raises error when codec_list not available."""
        from custom_components.zowietek.exceptions import ZowietekApiError
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        # Manually set codec_list to a non-list value
        coordinator.data.video["codec_list"] = "not_a_list"

        # Test the internal _set_encoder_type directly
        with pytest.raises(ZowietekApiError) as exc_info:
            await select._set_encoder_type("H.264")

        assert "not available" in str(exc_info.value)

    async def test_unknown_select_type_current_option_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select with unknown type returns None for current_option."""
        from dataclasses import replace

        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        # Create a modified description with unknown select_type
        desc = SELECT_DESCRIPTIONS[0]
        unknown_desc = replace(desc, select_type="unknown_type")

        select = ZowietekSelect(coordinator, unknown_desc)

        assert select.current_option is None

    async def test_unknown_select_type_options_returns_empty(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select with unknown type returns empty options."""
        from dataclasses import replace

        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        # Create a modified description with unknown select_type
        desc = SELECT_DESCRIPTIONS[0]
        unknown_desc = replace(desc, select_type="unknown_type")

        select = ZowietekSelect(coordinator, unknown_desc)

        assert select.options == []

    async def test_output_format_fallback_adds_current(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test output format fallback adds current format to options."""
        from custom_components.zowietek.select import (
            DEFAULT_OUTPUT_FORMATS,
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        # Set a custom format not in defaults and remove format_list
        coordinator.data.video["output_format"] = "CUSTOM_FORMAT"
        if "output_format_list" in coordinator.data.video:
            del coordinator.data.video["output_format_list"]

        select = ZowietekSelect(coordinator, descriptions["output_format"])

        # Should include default options and the custom current format
        assert "CUSTOM_FORMAT" in select.options
        assert all(f in select.options for f in DEFAULT_OUTPUT_FORMATS)

    async def test_options_returns_empty_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test options returns empty list when coordinator data is None."""
        from custom_components.zowietek.select import (
            SELECT_DESCRIPTIONS,
            ZowietekSelect,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SELECT_DESCRIPTIONS}

        # Set data to None
        coordinator.data = None

        select = ZowietekSelect(coordinator, descriptions["encoder_type"])

        assert select.options == []
