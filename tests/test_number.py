"""Tests for the Zowietek number entities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
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
        "volume": 75,
        "ao_volume": 100,
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
    """Mock ZowietekClient for number testing."""
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
        # Write methods for number entities
        client.async_set_audio_volume = AsyncMock()
        client.async_set_encoder_bitrate = AsyncMock()
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


class TestNumberDescriptions:
    """Tests for number entity descriptions."""

    def test_number_descriptions_defined(self) -> None:
        """Test that number descriptions are defined."""
        from custom_components.zowietek.number import NUMBER_DESCRIPTIONS

        assert NUMBER_DESCRIPTIONS is not None
        assert len(NUMBER_DESCRIPTIONS) >= 2  # At least audio_volume and stream_bitrate

    def test_audio_volume_description(self) -> None:
        """Test audio volume number description."""
        from custom_components.zowietek.number import NUMBER_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}
        assert "audio_volume" in descriptions

        desc = descriptions["audio_volume"]
        assert desc.translation_key == "audio_volume"
        assert desc.native_min_value == 0
        assert desc.native_max_value == 100
        assert desc.native_step == 1
        assert desc.icon == "mdi:volume-high"

    def test_stream_bitrate_description(self) -> None:
        """Test stream bitrate number description."""
        from custom_components.zowietek.number import NUMBER_DESCRIPTIONS

        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}
        assert "stream_bitrate" in descriptions

        desc = descriptions["stream_bitrate"]
        assert desc.translation_key == "stream_bitrate"
        assert desc.native_min_value == 1
        assert desc.native_max_value == 50
        assert desc.native_step == 1
        assert desc.icon == "mdi:speedometer"


class TestZowietekNumberInit:
    """Tests for ZowietekNumber initialization."""

    async def test_number_inherits_from_zowietek_entity(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test ZowietekNumber inherits from ZowietekEntity."""
        from custom_components.zowietek.entity import ZowietekEntity
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        description = NUMBER_DESCRIPTIONS[0]
        number = ZowietekNumber(coordinator, description)

        assert isinstance(number, ZowietekEntity)

    async def test_number_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number unique_id follows format {unique_id}_{key}."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        assert number.unique_id == "zowiebox-test-12345_audio_volume"

    async def test_number_entity_description_set(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number has entity_description attribute set."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        assert number.entity_description == descriptions["audio_volume"]


class TestAudioVolumeNumber:
    """Tests for audio volume number entity."""

    async def test_audio_volume_native_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test audio volume number returns current volume."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        # Mock audio_info has volume: 75
        assert number.native_value == 75

    async def test_audio_volume_set_value_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setting audio volume calls the API."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        await number.async_set_native_value(50)

        mock_zowietek_client.async_set_audio_volume.assert_called_once_with(50)

    async def test_audio_volume_set_value_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setting audio volume requests coordinator refresh."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        await number.async_set_native_value(50)

        coordinator.async_request_refresh.assert_called_once()


class TestStreamBitrateNumber:
    """Tests for stream bitrate number entity."""

    async def test_stream_bitrate_native_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test stream bitrate number returns current bitrate in Mbps."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["stream_bitrate"])

        # Mock venc_info has bitrate: 12000000 (12 Mbps)
        assert number.native_value == 12

    async def test_stream_bitrate_set_value_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setting stream bitrate calls the API."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["stream_bitrate"])

        await number.async_set_native_value(20)

        # API should receive bitrate in bps (20 Mbps = 20000000 bps)
        mock_zowietek_client.async_set_encoder_bitrate.assert_called_once_with(20000000)

    async def test_stream_bitrate_set_value_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setting stream bitrate requests coordinator refresh."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["stream_bitrate"])

        await number.async_set_native_value(20)

        coordinator.async_request_refresh.assert_called_once()


class TestNumberSetup:
    """Tests for number platform setup."""

    async def test_async_setup_entry_creates_numbers(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all number entities."""
        from custom_components.zowietek.number import NUMBER_DESCRIPTIONS

        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)

        number_entries = [e for e in entries if e.domain == "number"]
        assert len(number_entries) == len(NUMBER_DESCRIPTIONS)

    async def test_number_entities_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number entities are registered in entity registry."""
        from custom_components.zowietek.number import NUMBER_DESCRIPTIONS

        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        for description in NUMBER_DESCRIPTIONS:
            entity_id = f"number.zowiebox_studio_{description.key}"
            entry = entity_registry.async_get(entity_id)
            assert entry is not None, f"Number {entity_id} not registered"

    async def test_number_states_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number states are available in Home Assistant."""
        await _setup_integration(hass, mock_config_entry)

        # Check audio volume state (float format)
        state = hass.states.get("number.zowiebox_studio_audio_volume")
        assert state is not None
        assert state.state == "75.0"

        # Check stream bitrate state (12000000 bps = 12 Mbps, float format)
        state = hass.states.get("number.zowiebox_studio_stream_bitrate")
        assert state is not None
        assert state.state == "12.0"


class TestNumberAvailability:
    """Tests for number availability."""

    async def test_number_available_when_coordinator_has_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number is available when coordinator has data."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        assert number.available is True

    async def test_number_unavailable_when_coordinator_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number is unavailable when coordinator update fails."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.last_update_success = False

        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}
        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        assert number.available is False


class TestNumberDeviceInfo:
    """Tests for number device info."""

    async def test_number_has_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number has device_info property from base entity."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])
        device_info = number.device_info

        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "zowiebox-test-12345")}
        assert device_info["manufacturer"] == "Zowietek"


class TestNumberEdgeCases:
    """Tests for edge cases in number behavior."""

    async def test_coordinator_data_none_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number returns None when coordinator data is None."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        # Manually set coordinator.data to None
        coordinator.data = None

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        assert number.native_value is None

    async def test_audio_volume_missing_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test audio volume returns None when volume not in data."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        # Return audio info without volume
        mock_zowietek_client.async_get_audio_info.return_value = {
            "switch": 1,
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        assert number.native_value is None

    async def test_stream_bitrate_no_venc_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test stream bitrate returns None when venc data is empty."""
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        # Return empty venc data
        mock_zowietek_client.async_get_venc_info.return_value = {"venc": []}

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        number = ZowietekNumber(coordinator, descriptions["stream_bitrate"])

        assert number.native_value is None

    async def test_set_value_api_error_raises_ha_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test set_value raises HomeAssistantError when API fails."""
        from homeassistant.exceptions import HomeAssistantError

        from custom_components.zowietek.exceptions import ZowietekApiError
        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in NUMBER_DESCRIPTIONS}

        # Make API call raise an error
        mock_zowietek_client.async_set_audio_volume.side_effect = ZowietekApiError(
            "Invalid value", "00003"
        )

        number = ZowietekNumber(coordinator, descriptions["audio_volume"])

        with pytest.raises(HomeAssistantError) as exc_info:
            await number.async_set_native_value(50)

        assert "Failed to set" in str(exc_info.value)

    async def test_unknown_number_type_native_value_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test number with unknown type returns None for native_value."""
        from dataclasses import replace

        from custom_components.zowietek.number import (
            NUMBER_DESCRIPTIONS,
            ZowietekNumber,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        # Create a modified description with unknown number_type
        desc = NUMBER_DESCRIPTIONS[0]
        unknown_desc = replace(desc, key="unknown_type", number_type="unknown")

        number = ZowietekNumber(coordinator, unknown_desc)

        assert number.native_value is None


class TestNumberServiceCalls:
    """Tests for number entity service calls."""

    async def test_set_value_via_service_call(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setting number value via service call."""
        await _setup_integration(hass, mock_config_entry)

        # Call the service to set audio volume
        await hass.services.async_call(
            "number",
            SERVICE_SET_VALUE,
            {
                "entity_id": "number.zowiebox_studio_audio_volume",
                ATTR_VALUE: 50,
            },
            blocking=True,
        )

        mock_zowietek_client.async_set_audio_volume.assert_called_once_with(50)

    async def test_set_bitrate_via_service_call(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setting bitrate value via service call."""
        await _setup_integration(hass, mock_config_entry)

        # Call the service to set stream bitrate
        await hass.services.async_call(
            "number",
            SERVICE_SET_VALUE,
            {
                "entity_id": "number.zowiebox_studio_stream_bitrate",
                ATTR_VALUE: 20,
            },
            blocking=True,
        )

        # API should receive bitrate in bps (20 Mbps = 20000000 bps)
        mock_zowietek_client.async_set_encoder_bitrate.assert_called_once_with(20000000)
