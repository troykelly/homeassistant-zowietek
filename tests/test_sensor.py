"""Tests for the Zowietek sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek.const import DOMAIN
from custom_components.zowietek.sensor import (
    SENSOR_DESCRIPTIONS,
    ZowietekSensor,
    ZowietekSensorEntityDescription,
)

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
    }


@pytest.fixture
def mock_video_info() -> dict[str, str | int]:
    """Return mock video info response."""
    return {
        "status": "00000",
        "rsp": "succeed",
    }


@pytest.fixture
def mock_input_signal() -> dict[str, str | int]:
    """Return mock input signal response."""
    return {
        "hdmi_signal": 1,
        "audio_signal": 48000,
        "width": 1920,
        "height": 1080,
        "framerate": 60,
        "desc": "1080p60",
    }


@pytest.fixture
def mock_output_info() -> dict[str, str | int]:
    """Return mock output info response."""
    return {
        "switch": 1,
        "format": "1080p60",
        "audio_switch": 1,
        "loop_out_switch": 0,
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
                "url": "",
            },
        ],
    }


@pytest.fixture
def mock_ndi_config() -> dict[str, str | int]:
    """Return mock NDI config response."""
    return {
        "activate": 1,
        "switch": 1,
        "mode_id": 1,
        "machinename": "ZowieBox-Studio",
        "groups": "Public",
    }


@pytest.fixture
def mock_venc_info() -> dict[str, Any]:
    """Return mock venc info response."""
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
def mock_audio_info() -> dict[str, Any]:
    """Return mock audio info response."""
    return {
        "switch": 1,
        "volume": 100,
    }


@pytest.fixture
def mock_sys_attr_info() -> dict[str, str]:
    """Return mock sys attr info response."""
    return {
        "SN": "zowiebox-test-12345",
        "firmware_version": "2.0.0.12",
        "hardware_version": "3.1.12.22",
        "model": "ZowieBox",
        "manufacturer": "Zowietek",
        "device_name": "ZowieBox-Studio",
        "ndi_version": "5.6.1",
    }


@pytest.fixture
def mock_dashboard_info() -> dict[str, str | float]:
    """Return mock dashboard info response."""
    return {
        "persistent_time": "01:23:45",
        "device_strat_time": "2024-01-01 00:00:00",
        "cpu_temp": 45.5,
        "cpu_payload": 32.1,
        "memory_info": {
            "used": 512,
            "total": 1024,
        },
    }


@pytest.fixture
def mock_zowietek_client(
    mock_device_info: dict[str, str],
    mock_video_info: dict[str, str | int],
    mock_input_signal: dict[str, str | int],
    mock_output_info: dict[str, str | int],
    mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
    mock_ndi_config: dict[str, str | int],
    mock_venc_info: dict[str, Any],
    mock_audio_info: dict[str, Any],
    mock_sys_attr_info: dict[str, str],
    mock_dashboard_info: dict[str, str | float],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for sensor testing."""
    with patch(
        "custom_components.zowietek.coordinator.ZowietekClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_get_video_info = AsyncMock(return_value=mock_video_info)
        client.async_get_input_signal = AsyncMock(return_value=mock_input_signal)
        client.async_get_output_info = AsyncMock(return_value=mock_output_info)
        client.async_get_stream_publish_info = AsyncMock(return_value=mock_stream_publish_info)
        client.async_get_ndi_config = AsyncMock(return_value=mock_ndi_config)
        client.async_get_venc_info = AsyncMock(return_value=mock_venc_info)
        client.async_get_audio_info = AsyncMock(return_value=mock_audio_info)
        client.async_get_sys_attr_info = AsyncMock(return_value=mock_sys_attr_info)
        client.async_get_dashboard_info = AsyncMock(return_value=mock_dashboard_info)
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


class TestSensorDescriptions:
    """Tests for sensor entity descriptions."""

    def test_sensor_descriptions_defined(self) -> None:
        """Test that sensor descriptions are defined."""
        assert SENSOR_DESCRIPTIONS is not None
        assert len(SENSOR_DESCRIPTIONS) == 12

    def test_video_resolution_description(self) -> None:
        """Test video resolution sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "video_resolution" in descriptions

        desc = descriptions["video_resolution"]
        assert desc.translation_key == "video_resolution"
        assert desc.icon == "mdi:video"

    def test_frame_rate_description(self) -> None:
        """Test frame rate sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "frame_rate" in descriptions

        desc = descriptions["frame_rate"]
        assert desc.translation_key == "frame_rate"
        assert desc.native_unit_of_measurement == "fps"
        assert desc.state_class == SensorStateClass.MEASUREMENT
        assert desc.icon == "mdi:camera-timer"

    def test_stream_bitrate_description(self) -> None:
        """Test stream bitrate sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "stream_bitrate" in descriptions

        desc = descriptions["stream_bitrate"]
        assert desc.translation_key == "stream_bitrate"
        assert desc.native_unit_of_measurement == "bps"
        assert desc.state_class == SensorStateClass.MEASUREMENT
        assert desc.icon == "mdi:speedometer"

    def test_encoder_type_description(self) -> None:
        """Test encoder type sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "encoder_type" in descriptions

        desc = descriptions["encoder_type"]
        assert desc.translation_key == "encoder_type"
        assert desc.icon == "mdi:video-box"

    def test_ndi_name_description(self) -> None:
        """Test NDI name sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "ndi_name" in descriptions

        desc = descriptions["ndi_name"]
        assert desc.translation_key == "ndi_name"
        assert desc.icon == "mdi:broadcast"

    def test_output_format_description(self) -> None:
        """Test output format sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "output_format" in descriptions

        desc = descriptions["output_format"]
        assert desc.translation_key == "output_format"
        assert desc.icon == "mdi:monitor"
        assert desc.entity_category == EntityCategory.DIAGNOSTIC


class TestZowietekSensor:
    """Tests for ZowietekSensor class."""

    async def test_sensor_inherits_from_zowietek_entity(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test ZowietekSensor inherits from ZowietekEntity."""
        from custom_components.zowietek.entity import ZowietekEntity

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        # Get any sensor description
        description = SENSOR_DESCRIPTIONS[0]
        sensor = ZowietekSensor(coordinator, description)

        assert isinstance(sensor, ZowietekEntity)

    async def test_sensor_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor unique_id follows format {unique_id}_{key}."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["video_resolution"])

        assert sensor.unique_id == "zowiebox-test-12345_video_resolution"

    async def test_sensor_entity_description_set(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor has entity_description attribute set."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["frame_rate"])

        assert sensor.entity_description == descriptions["frame_rate"]


class TestZowietekSensorValues:
    """Tests for ZowietekSensor native_value property."""

    async def test_video_resolution_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video resolution sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["video_resolution"])

        assert sensor.native_value == "1920x1080"

    async def test_frame_rate_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test frame rate sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["frame_rate"])

        assert sensor.native_value == 60

    async def test_stream_bitrate_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test stream bitrate sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["stream_bitrate"])

        assert sensor.native_value == 12000000

    async def test_encoder_type_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test encoder type sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["encoder_type"])

        assert sensor.native_value == "H.264"

    async def test_ndi_name_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI name sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["ndi_name"])

        assert sensor.native_value == "ZowieBox-Studio"

    async def test_output_format_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test output format sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["output_format"])

        assert sensor.native_value == "1080p60"

    async def test_missing_value_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor returns None for missing data."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        # Create a description with a non-existent key
        desc = ZowietekSensorEntityDescription(
            key="nonexistent",
            name="Nonexistent",
            value_key="video.nonexistent_key",
        )

        sensor = ZowietekSensor(coordinator, desc)

        assert sensor.native_value is None

    async def test_coordinator_data_none_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor returns None when coordinator data is None."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        # Set coordinator data to None
        coordinator.data = None

        sensor = ZowietekSensor(coordinator, descriptions["video_resolution"])

        assert sensor.native_value is None


class TestSensorSetup:
    """Tests for sensor setup."""

    async def test_sensor_entities_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor entities are registered in entity registry."""
        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        # Check each sensor is registered
        for description in SENSOR_DESCRIPTIONS:
            entity_id = f"sensor.zowiebox_studio_{description.key}"
            entry = entity_registry.async_get(entity_id)
            assert entry is not None, f"Sensor {entity_id} not registered"

    async def test_sensor_states_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor states are available in Home Assistant."""
        await _setup_integration(hass, mock_config_entry)

        # Check video resolution
        state = hass.states.get("sensor.zowiebox_studio_video_resolution")
        assert state is not None
        assert state.state == "1920x1080"

        # Check frame rate
        state = hass.states.get("sensor.zowiebox_studio_frame_rate")
        assert state is not None
        assert state.state == "60"

        # Check stream bitrate
        state = hass.states.get("sensor.zowiebox_studio_stream_bitrate")
        assert state is not None
        assert state.state == "12000000"

        # Check encoder type
        state = hass.states.get("sensor.zowiebox_studio_encoder_type")
        assert state is not None
        assert state.state == "H.264"

        # Check NDI name
        state = hass.states.get("sensor.zowiebox_studio_ndi_name")
        assert state is not None
        assert state.state == "ZowieBox-Studio"

        # Check output format
        state = hass.states.get("sensor.zowiebox_studio_output_format")
        assert state is not None
        assert state.state == "1080p60"


class TestSensorEntityCategory:
    """Tests for sensor entity categories."""

    async def test_diagnostic_sensors_have_category(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test diagnostic sensors have EntityCategory.DIAGNOSTIC."""
        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        # Output format should be diagnostic
        output_entry = entity_registry.async_get("sensor.zowiebox_studio_output_format")
        assert output_entry is not None
        assert output_entry.entity_category == EntityCategory.DIAGNOSTIC

    async def test_non_diagnostic_sensors_no_category(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test non-diagnostic sensors have no entity category."""
        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        # Video resolution should not be diagnostic
        resolution_entry = entity_registry.async_get("sensor.zowiebox_studio_video_resolution")
        assert resolution_entry is not None
        assert resolution_entry.entity_category is None

        # Frame rate should not be diagnostic
        framerate_entry = entity_registry.async_get("sensor.zowiebox_studio_frame_rate")
        assert framerate_entry is not None
        assert framerate_entry.entity_category is None


class TestSensorIcons:
    """Tests for sensor icons."""

    async def test_video_resolution_icon(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video resolution sensor has correct icon."""
        await _setup_integration(hass, mock_config_entry)

        state = hass.states.get("sensor.zowiebox_studio_video_resolution")
        assert state is not None
        assert state.attributes.get("icon") == "mdi:video"

    async def test_frame_rate_icon(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test frame rate sensor has correct icon."""
        await _setup_integration(hass, mock_config_entry)

        state = hass.states.get("sensor.zowiebox_studio_frame_rate")
        assert state is not None
        assert state.attributes.get("icon") == "mdi:camera-timer"

    async def test_ndi_name_icon(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI name sensor has correct icon."""
        await _setup_integration(hass, mock_config_entry)

        state = hass.states.get("sensor.zowiebox_studio_ndi_name")
        assert state is not None
        assert state.attributes.get("icon") == "mdi:broadcast"


class TestSensorAvailability:
    """Tests for sensor availability."""

    async def test_sensor_available_when_coordinator_has_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor is available when coordinator has data."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["video_resolution"])

        assert sensor.available is True

    async def test_sensor_unavailable_when_coordinator_update_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor is unavailable when coordinator update fails."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        # Simulate coordinator update failure
        coordinator.last_update_success = False

        sensor = ZowietekSensor(coordinator, descriptions["video_resolution"])

        assert sensor.available is False


class TestSensorEdgeCases:
    """Tests for sensor native_value edge cases."""

    async def test_invalid_value_key_format_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor returns None when value_key has invalid format (no dot)."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        # Create a description with a value_key that doesn't have a dot
        desc = ZowietekSensorEntityDescription(
            key="bad_format",
            name="Bad Format",
            value_key="nodotinthiskey",  # Missing section.key format
        )

        sensor = ZowietekSensor(coordinator, desc)

        assert sensor.native_value is None

    async def test_nonexistent_section_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor returns None when section doesn't exist."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        # Create a description referencing a non-existent section
        desc = ZowietekSensorEntityDescription(
            key="bad_section",
            name="Bad Section",
            value_key="nonexistent_section.some_key",
        )

        sensor = ZowietekSensor(coordinator, desc)

        assert sensor.native_value is None

    async def test_non_standard_type_converted_to_string(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor converts non-standard types to string."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        # Add a non-standard value to video data (list)
        coordinator.data.video["test_list_value"] = ["item1", "item2"]

        desc = ZowietekSensorEntityDescription(
            key="test_list",
            name="Test List",
            value_key="video.test_list_value",
        )

        sensor = ZowietekSensor(coordinator, desc)

        # Should convert list to string
        assert sensor.native_value == "['item1', 'item2']"
