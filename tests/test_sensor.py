"""Tests for the Zowietek sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING
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
    """Return mock stream publish info response."""
    return {
        "publish": [
            {
                "type": "rtmp",
                "enable": 1,
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
    """Mock ZowietekClient for sensor testing."""
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
        assert len(SENSOR_DESCRIPTIONS) > 0

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
        assert desc.native_unit_of_measurement == "kbps"
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

    def test_firmware_version_description(self) -> None:
        """Test firmware version sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "firmware_version" in descriptions

        desc = descriptions["firmware_version"]
        assert desc.translation_key == "firmware_version"
        assert desc.icon == "mdi:chip"
        assert desc.entity_category == EntityCategory.DIAGNOSTIC

    def test_uptime_description(self) -> None:
        """Test uptime sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "uptime" in descriptions

        desc = descriptions["uptime"]
        assert desc.translation_key == "uptime"
        assert desc.icon == "mdi:clock-outline"
        assert desc.entity_category == EntityCategory.DIAGNOSTIC

    def test_device_mode_description(self) -> None:
        """Test device mode sensor description."""
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        assert "device_mode" in descriptions

        desc = descriptions["device_mode"]
        assert desc.translation_key == "device_mode"
        assert desc.icon == "mdi:video-switch"


class TestZowietekSensorInit:
    """Tests for ZowietekSensor initialization."""

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

        assert sensor.native_value == 8000

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

        assert sensor.native_value == "h264"

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

    async def test_firmware_version_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test firmware version sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["firmware_version"])

        assert sensor.native_value == "1.2.3"

    async def test_uptime_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test uptime sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["uptime"])

        # Uptime should be formatted or raw value
        assert sensor.native_value == "123456"

    async def test_device_mode_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device mode sensor returns correct value."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["device_mode"])

        assert sensor.native_value == "encoder"

    async def test_missing_value_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor returns None when value is missing from coordinator data."""
        # Remove NDI name from mock response
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "ndi_enable": 1,
            # ndi_name is missing
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["ndi_name"])

        assert sensor.native_value is None


class TestSensorSetup:
    """Tests for sensor platform setup."""

    async def test_async_setup_entry_creates_sensors(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all sensor entities."""
        await _setup_integration(hass, mock_config_entry)

        # Verify sensors are created
        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)

        sensor_entries = [e for e in entries if e.domain == "sensor"]
        assert len(sensor_entries) == len(SENSOR_DESCRIPTIONS)

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
            entity_id = f"sensor.zowiebox_test_{description.key}"
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

        # Check video resolution state
        state = hass.states.get("sensor.zowiebox_test_video_resolution")
        assert state is not None
        assert state.state == "1920x1080"

        # Check frame rate state
        state = hass.states.get("sensor.zowiebox_test_frame_rate")
        assert state is not None
        assert state.state == "60"


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

    async def test_sensor_unavailable_when_coordinator_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor is unavailable when coordinator update fails."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.last_update_success = False

        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
        sensor = ZowietekSensor(coordinator, descriptions["video_resolution"])

        assert sensor.available is False


class TestSensorDeviceInfo:
    """Tests for sensor device info."""

    async def test_sensor_has_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test sensor has device_info property from base entity."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

        sensor = ZowietekSensor(coordinator, descriptions["video_resolution"])
        device_info = sensor.device_info

        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "zowiebox-test-12345")}
        assert device_info["manufacturer"] == "Zowietek"


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

        # Firmware version should be diagnostic
        firmware_entry = entity_registry.async_get("sensor.zowiebox_test_firmware_version")
        assert firmware_entry is not None
        assert firmware_entry.entity_category == EntityCategory.DIAGNOSTIC

        # Uptime should be diagnostic
        uptime_entry = entity_registry.async_get("sensor.zowiebox_test_uptime")
        assert uptime_entry is not None
        assert uptime_entry.entity_category == EntityCategory.DIAGNOSTIC

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
        resolution_entry = entity_registry.async_get("sensor.zowiebox_test_video_resolution")
        assert resolution_entry is not None
        assert resolution_entry.entity_category is None
