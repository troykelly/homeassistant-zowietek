"""Tests for the Zowietek base entity class."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek.const import DOMAIN
from custom_components.zowietek.coordinator import ZowietekCoordinator
from custom_components.zowietek.entity import ZowietekEntity

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
        "softver": "1.0.0",
        "hardver": "2.0",
        "mac": "00:11:22:33:44:55",
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
        "machinename": "ZowieBox-Test",
        "groups": "Public",
    }


@pytest.fixture
def mock_zowietek_client(
    mock_device_info: dict[str, str],
    mock_video_info: dict[str, str | int],
    mock_input_signal: dict[str, str | int],
    mock_output_info: dict[str, str | int],
    mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
    mock_ndi_config: dict[str, str | int],
    mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
    mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for entity testing."""
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
        client.close = AsyncMock()
        client.host = "http://192.168.1.100"
        yield client


async def _refresh_coordinator(coordinator: ZowietekCoordinator) -> None:
    """Helper to refresh coordinator data."""
    coordinator.data = await coordinator._async_update_data()


class TestZowietekEntityInit:
    """Tests for ZowietekEntity initialization."""

    async def test_entity_inherits_from_coordinator_entity(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test ZowietekEntity inherits from CoordinatorEntity."""
        from homeassistant.helpers.update_coordinator import CoordinatorEntity

        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")

        assert isinstance(entity, CoordinatorEntity)

    async def test_entity_has_entity_name_attribute(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test entity has _attr_has_entity_name set to True."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")

        assert entity._attr_has_entity_name is True

    async def test_entity_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test entity unique_id uses correct format: {unique_id}_{entity_key}."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "video_resolution")

        assert entity.unique_id == "zowiebox-test-12345_video_resolution"

    async def test_entity_stores_coordinator_reference(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test entity stores reference to coordinator."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")

        assert entity.coordinator is coordinator


class TestZowietekEntityDeviceInfo:
    """Tests for ZowietekEntity device_info property."""

    async def test_device_info_returns_dict(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info returns a dict with required keys.

        DeviceInfo is a TypedDict so we verify it's a dict with expected keys.
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        # DeviceInfo is a TypedDict, so verify it's a dict with expected keys
        assert isinstance(device_info, dict)
        assert "identifiers" in device_info
        assert "manufacturer" in device_info
        assert "name" in device_info

    async def test_device_info_identifiers(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info identifiers use domain and unique_id."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        assert device_info["identifiers"] == {(DOMAIN, "zowiebox-test-12345")}

    async def test_device_info_manufacturer(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info manufacturer is Zowietek."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        assert device_info["manufacturer"] == "Zowietek"

    async def test_device_info_model_from_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info model defaults to ZowieBox.

        Since the device info endpoint is not available on all firmware,
        model info is not retrieved from the API and defaults to 'ZowieBox'.
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        # Model defaults to ZowieBox since device info endpoint not used
        assert device_info["model"] == "ZowieBox"

    async def test_device_info_model_fallback(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info model falls back to ZowieBox when not in API."""
        mock_config_entry.add_to_hass(hass)

        # Device info without model field
        mock_zowietek_client.async_get_device_info.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "devicesn": "zowiebox-test-12345",
            "devicename": "ZowieBox-Test",
            "softver": "1.0.0",
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        assert device_info["model"] == "ZowieBox"

    async def test_device_info_name_from_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info name comes from NDI machinename."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        # Name comes from NDI config machinename
        assert device_info["name"] == "ZowieBox-Test"

    async def test_device_info_name_fallback(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info name falls back to config entry title when machinename missing."""
        mock_config_entry.add_to_hass(hass)

        # NDI config without machinename
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "switch": 1,
            # No machinename field
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        # Should fall back to config entry title
        assert device_info["name"] == "Test ZowieBox"

    async def test_device_info_sw_version(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info sw_version is None when device info not available.

        Since the device info endpoint is not available on all firmware,
        software version is not available and should be None.
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        # sw_version is None since device info endpoint not used
        assert device_info.get("sw_version") is None

    async def test_device_info_sw_version_none_when_missing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info sw_version is None when not in API."""
        mock_config_entry.add_to_hass(hass)

        # Device info without softver
        mock_zowietek_client.async_get_device_info.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "devicesn": "zowiebox-test-12345",
            "devicename": "ZowieBox-Test",
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        assert device_info.get("sw_version") is None

    async def test_device_info_configuration_url(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_info configuration_url points to device web UI."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")
        device_info = entity.device_info

        assert device_info["configuration_url"] == "http://192.168.1.100"


class TestZowietekEntityAvailability:
    """Tests for ZowietekEntity availability."""

    async def test_entity_available_when_coordinator_has_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test entity is available when coordinator has data."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity = ZowietekEntity(coordinator, "test_sensor")

        assert entity.available is True

    async def test_entity_unavailable_when_coordinator_update_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test entity is unavailable when coordinator last update failed."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Simulate failed update
        coordinator.last_update_success = False

        entity = ZowietekEntity(coordinator, "test_sensor")

        assert entity.available is False


class TestZowietekEntityMultipleEntities:
    """Tests for multiple ZowietekEntity instances."""

    async def test_multiple_entities_have_unique_ids(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test multiple entities have unique IDs."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity1 = ZowietekEntity(coordinator, "video_resolution")
        entity2 = ZowietekEntity(coordinator, "streaming_status")
        entity3 = ZowietekEntity(coordinator, "ndi_enabled")

        assert entity1.unique_id != entity2.unique_id
        assert entity2.unique_id != entity3.unique_id
        assert entity1.unique_id != entity3.unique_id

    async def test_multiple_entities_share_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test multiple entities share the same device info."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        entity1 = ZowietekEntity(coordinator, "video_resolution")
        entity2 = ZowietekEntity(coordinator, "streaming_status")

        # Both entities should have identical device_info (same device)
        assert entity1.device_info["identifiers"] == entity2.device_info["identifiers"]
        assert entity1.device_info["name"] == entity2.device_info["name"]
