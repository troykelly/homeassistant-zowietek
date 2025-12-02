"""Tests for the Zowietek binary sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    STATE_OFF,
    STATE_ON,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    ZowietekBinarySensor,
)
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
            {
                "type": "srt",
                "switch": 0,
                "url": "srt://example.com:9000",
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
def mock_zowietek_client(
    mock_device_info: dict[str, str],
    mock_video_info: dict[str, str | int],
    mock_input_signal: dict[str, str | int],
    mock_output_info: dict[str, str | int],
    mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
    mock_ndi_config: dict[str, str | int],
    mock_venc_info: dict[str, Any],
    mock_audio_info: dict[str, Any],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for binary sensor testing."""
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


class TestBinarySensorDescriptions:
    """Tests for binary sensor entity descriptions."""

    def test_binary_sensor_descriptions_defined(self) -> None:
        """Test that binary sensor descriptions are defined."""
        assert BINARY_SENSOR_DESCRIPTIONS is not None
        assert len(BINARY_SENSOR_DESCRIPTIONS) > 0

    def test_streaming_description(self) -> None:
        """Test streaming binary sensor description."""
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}
        assert "streaming" in descriptions

        desc = descriptions["streaming"]
        assert desc.translation_key == "streaming"
        assert desc.device_class == BinarySensorDeviceClass.RUNNING

    def test_video_input_description(self) -> None:
        """Test video input binary sensor description."""
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}
        assert "video_input" in descriptions

        desc = descriptions["video_input"]
        assert desc.translation_key == "video_input"
        assert desc.device_class == BinarySensorDeviceClass.CONNECTIVITY

    def test_ndi_enabled_description(self) -> None:
        """Test NDI enabled binary sensor description."""
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}
        assert "ndi_enabled" in descriptions

        desc = descriptions["ndi_enabled"]
        assert desc.translation_key == "ndi_enabled"
        assert desc.entity_category == EntityCategory.DIAGNOSTIC

    def test_rtmp_enabled_description(self) -> None:
        """Test RTMP enabled binary sensor description."""
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}
        assert "rtmp_enabled" in descriptions

        desc = descriptions["rtmp_enabled"]
        assert desc.translation_key == "rtmp_enabled"
        assert desc.entity_category == EntityCategory.DIAGNOSTIC

    def test_srt_enabled_description(self) -> None:
        """Test SRT enabled binary sensor description."""
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}
        assert "srt_enabled" in descriptions

        desc = descriptions["srt_enabled"]
        assert desc.translation_key == "srt_enabled"
        assert desc.entity_category == EntityCategory.DIAGNOSTIC


class TestZowietekBinarySensorInit:
    """Tests for ZowietekBinarySensor initialization."""

    async def test_binary_sensor_inherits_from_zowietek_entity(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test ZowietekBinarySensor inherits from ZowietekEntity."""
        from custom_components.zowietek.entity import ZowietekEntity

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        # Get any binary sensor description
        description = BINARY_SENSOR_DESCRIPTIONS[0]
        binary_sensor = ZowietekBinarySensor(coordinator, description)

        assert isinstance(binary_sensor, ZowietekEntity)

    async def test_binary_sensor_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor unique_id follows format {unique_id}_{key}."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["streaming"])

        assert binary_sensor.unique_id == "zowiebox-test-12345_streaming"

    async def test_binary_sensor_entity_description_set(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor has entity_description attribute set."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["video_input"])

        assert binary_sensor.entity_description == descriptions["video_input"]


class TestZowietekBinarySensorValues:
    """Tests for ZowietekBinarySensor is_on property."""

    async def test_streaming_is_on_when_any_stream_enabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test streaming binary sensor is on when any stream is enabled."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["streaming"])

        # NDI is enabled (ndi_enable=1), so streaming should be True
        assert binary_sensor.is_on is True

    async def test_streaming_is_off_when_no_streams_enabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test streaming binary sensor is off when no streams are enabled."""
        # Disable NDI
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "switch": 0,
            "ndi_name": "ZowieBox-Studio",
        }
        # Disable RTMP and SRT
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {"type": "rtmp", "switch": 0, "url": ""},
                {"type": "srt", "switch": 0, "url": ""},
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["streaming"])

        assert binary_sensor.is_on is False

    async def test_video_input_is_on_when_signal_detected(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video input binary sensor is on when signal is detected."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["video_input"])

        # signal=1 means input detected
        assert binary_sensor.is_on is True

    async def test_video_input_is_on_when_hdmi_signal_detected(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video input binary sensor works with hdmi_signal key from live devices."""
        # Live device uses hdmi_signal instead of signal
        mock_zowietek_client.async_get_input_signal.return_value = {
            "hdmi_signal": 1,
            "audio_signal": 0,
            "width": 1920,
            "height": 1080,
            "framerate": 60,
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["video_input"])

        # hdmi_signal=1 means input detected
        assert binary_sensor.is_on is True

    async def test_video_input_is_off_when_hdmi_signal_is_zero(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video input binary sensor is off when hdmi_signal is 0."""
        mock_zowietek_client.async_get_input_signal.return_value = {
            "hdmi_signal": 0,
            "audio_signal": 0,
            "width": 0,
            "height": 0,
            "framerate": 0,
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["video_input"])

        assert binary_sensor.is_on is False

    async def test_video_input_is_off_when_no_signal(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video input binary sensor is off when no signal."""
        mock_zowietek_client.async_get_input_signal.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "signal": 0,
            "width": 0,
            "height": 0,
            "fps": 0,
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["video_input"])

        assert binary_sensor.is_on is False

    async def test_ndi_enabled_is_on(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI enabled binary sensor is on when NDI is enabled."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["ndi_enabled"])

        assert binary_sensor.is_on is True

    async def test_ndi_enabled_is_off(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI enabled binary sensor is off when NDI is disabled."""
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "switch": 0,
            "ndi_name": "ZowieBox-Studio",
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["ndi_enabled"])

        assert binary_sensor.is_on is False

    async def test_rtmp_enabled_is_on(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test RTMP enabled binary sensor is on when RTMP is enabled."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["rtmp_enabled"])

        # RTMP is enabled in mock (enable=1)
        assert binary_sensor.is_on is True

    async def test_rtmp_enabled_is_off(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test RTMP enabled binary sensor is off when RTMP is disabled."""
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {"type": "rtmp", "switch": 0, "url": ""},
                {"type": "srt", "switch": 0, "url": ""},
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["rtmp_enabled"])

        assert binary_sensor.is_on is False

    async def test_srt_enabled_is_on(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test SRT enabled binary sensor is on when SRT is enabled."""
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {"type": "rtmp", "switch": 1, "url": "rtmp://example.com/live"},
                {"type": "srt", "switch": 1, "url": "srt://example.com:9000"},
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["srt_enabled"])

        assert binary_sensor.is_on is True

    async def test_srt_enabled_is_off(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test SRT enabled binary sensor is off when SRT is disabled."""
        # Default mock has SRT disabled (enable=0)
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["srt_enabled"])

        assert binary_sensor.is_on is False

    async def test_coordinator_data_none_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor returns None when coordinator data is None."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        # Manually set coordinator.data to None
        coordinator.data = None

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["streaming"])

        assert binary_sensor.is_on is None

    async def test_streaming_is_on_when_only_srt_enabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test streaming binary sensor is on when only SRT is enabled."""
        # Disable NDI
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "switch": 0,
            "ndi_name": "ZowieBox-Studio",
        }
        # Disable RTMP but enable SRT
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {"type": "rtmp", "switch": 0, "url": ""},
                {"type": "srt", "switch": 1, "url": "srt://example.com:9000"},
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["streaming"])

        # Streaming should be on because SRT is enabled
        assert binary_sensor.is_on is True

    async def test_video_input_returns_false_when_input_not_dict(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video input binary sensor returns False when input data is not a dict."""
        # Set input to a non-dict value
        mock_zowietek_client.async_get_input_signal.return_value = "invalid"

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["video_input"])

        assert binary_sensor.is_on is False

    async def test_video_input_returns_false_when_signal_missing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video input binary sensor returns False when signal key is missing."""
        mock_zowietek_client.async_get_input_signal.return_value = {
            "status": "00000",
            "rsp": "succeed",
            # signal key is missing
            "width": 1920,
            "height": 1080,
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["video_input"])

        assert binary_sensor.is_on is False

    async def test_unknown_sensor_type_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor returns None for unknown sensor type."""
        from custom_components.zowietek.binary_sensor import (
            ZowietekBinarySensorEntityDescription,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        # Create a description with an unknown sensor_type
        unknown_description = ZowietekBinarySensorEntityDescription(
            key="unknown_sensor",
            name="Unknown",
            sensor_type="unknown_type",
        )

        binary_sensor = ZowietekBinarySensor(coordinator, unknown_description)

        assert binary_sensor.is_on is None

    async def test_ndi_enabled_returns_false_when_ndi_enable_missing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test NDI enabled returns False when ndi_enable key is missing."""
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            # ndi_enable key is missing
            "ndi_name": "ZowieBox-Studio",
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["ndi_enabled"])

        assert binary_sensor.is_on is False

    async def test_rtmp_enabled_returns_false_when_publish_not_list(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test RTMP enabled returns False when publish is not a list."""
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": "invalid",  # Not a list
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["rtmp_enabled"])

        assert binary_sensor.is_on is False

    async def test_rtmp_enabled_skips_non_dict_entries(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test RTMP enabled skips non-dict entries in publish list."""
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                "invalid_entry",  # Not a dict, should be skipped
                {"type": "rtmp", "switch": 1, "url": "rtmp://example.com"},
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["rtmp_enabled"])

        assert binary_sensor.is_on is True

    async def test_rtmp_enabled_returns_false_when_enable_missing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test RTMP enabled returns False when enable key is missing."""
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {"type": "rtmp", "url": "rtmp://example.com"},  # enable key missing
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["rtmp_enabled"])

        assert binary_sensor.is_on is False

    async def test_rtmp_enabled_returns_false_when_protocol_not_found(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test RTMP enabled returns False when rtmp not in publish list."""
        mock_zowietek_client.async_get_stream_publish_info.return_value = {
            "publish": [
                {"type": "srt", "switch": 1, "url": "srt://example.com"},
                # No rtmp entry
            ],
        }

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["rtmp_enabled"])

        assert binary_sensor.is_on is False


class TestBinarySensorSetup:
    """Tests for binary sensor platform setup."""

    async def test_async_setup_entry_creates_binary_sensors(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test async_setup_entry creates all binary sensor entities."""
        await _setup_integration(hass, mock_config_entry)

        # Verify binary sensors are created
        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)

        binary_sensor_entries = [e for e in entries if e.domain == "binary_sensor"]
        assert len(binary_sensor_entries) == len(BINARY_SENSOR_DESCRIPTIONS)

    async def test_binary_sensor_entities_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor entities are registered in entity registry."""
        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        # Check each binary sensor is registered
        for description in BINARY_SENSOR_DESCRIPTIONS:
            entity_id = f"binary_sensor.zowiebox_studio_{description.key}"
            entry = entity_registry.async_get(entity_id)
            assert entry is not None, f"Binary sensor {entity_id} not registered"

    async def test_binary_sensor_states_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor states are available in Home Assistant."""
        await _setup_integration(hass, mock_config_entry)

        # Check streaming state (should be on - NDI enabled)
        state = hass.states.get("binary_sensor.zowiebox_studio_streaming")
        assert state is not None
        assert state.state == STATE_ON

        # Check video input state (should be on - signal=1)
        state = hass.states.get("binary_sensor.zowiebox_studio_video_input")
        assert state is not None
        assert state.state == STATE_ON

        # Check NDI enabled state
        state = hass.states.get("binary_sensor.zowiebox_studio_ndi_enabled")
        assert state is not None
        assert state.state == STATE_ON

        # Check RTMP enabled state
        state = hass.states.get("binary_sensor.zowiebox_studio_rtmp_enabled")
        assert state is not None
        assert state.state == STATE_ON

        # Check SRT enabled state (should be off in default mock)
        state = hass.states.get("binary_sensor.zowiebox_studio_srt_enabled")
        assert state is not None
        assert state.state == STATE_OFF


class TestBinarySensorAvailability:
    """Tests for binary sensor availability."""

    async def test_binary_sensor_available_when_coordinator_has_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor is available when coordinator has data."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["streaming"])

        assert binary_sensor.available is True

    async def test_binary_sensor_unavailable_when_coordinator_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor is unavailable when coordinator update fails."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.last_update_success = False

        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}
        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["streaming"])

        assert binary_sensor.available is False


class TestBinarySensorDeviceInfo:
    """Tests for binary sensor device info."""

    async def test_binary_sensor_has_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test binary sensor has device_info property from base entity."""
        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        descriptions = {desc.key: desc for desc in BINARY_SENSOR_DESCRIPTIONS}

        binary_sensor = ZowietekBinarySensor(coordinator, descriptions["streaming"])
        device_info = binary_sensor.device_info

        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "zowiebox-test-12345")}
        assert device_info["manufacturer"] == "Zowietek"


class TestBinarySensorEntityCategory:
    """Tests for binary sensor entity categories."""

    async def test_diagnostic_binary_sensors_have_category(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test protocol binary sensors have EntityCategory.DIAGNOSTIC."""
        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        # NDI enabled should be diagnostic
        ndi_entry = entity_registry.async_get("binary_sensor.zowiebox_studio_ndi_enabled")
        assert ndi_entry is not None
        assert ndi_entry.entity_category == EntityCategory.DIAGNOSTIC

        # RTMP enabled should be diagnostic
        rtmp_entry = entity_registry.async_get("binary_sensor.zowiebox_studio_rtmp_enabled")
        assert rtmp_entry is not None
        assert rtmp_entry.entity_category == EntityCategory.DIAGNOSTIC

        # SRT enabled should be diagnostic
        srt_entry = entity_registry.async_get("binary_sensor.zowiebox_studio_srt_enabled")
        assert srt_entry is not None
        assert srt_entry.entity_category == EntityCategory.DIAGNOSTIC

    async def test_non_diagnostic_binary_sensors_no_category(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test non-diagnostic binary sensors have no entity category."""
        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)

        # Streaming should not be diagnostic
        streaming_entry = entity_registry.async_get("binary_sensor.zowiebox_studio_streaming")
        assert streaming_entry is not None
        assert streaming_entry.entity_category is None

        # Video input should not be diagnostic
        video_entry = entity_registry.async_get("binary_sensor.zowiebox_studio_video_input")
        assert video_entry is not None
        assert video_entry.entity_category is None


class TestBinarySensorIcons:
    """Tests for binary sensor icons."""

    async def test_streaming_icon(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test streaming binary sensor has correct icon."""
        await _setup_integration(hass, mock_config_entry)

        state = hass.states.get("binary_sensor.zowiebox_studio_streaming")
        assert state is not None
        # Icon should be mdi:broadcast when on
        assert state.attributes.get("icon") == "mdi:broadcast"

    async def test_video_input_icon(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test video input binary sensor has correct icon."""
        await _setup_integration(hass, mock_config_entry)

        state = hass.states.get("binary_sensor.zowiebox_studio_video_input")
        assert state is not None
        assert state.attributes.get("icon") == "mdi:video-input-hdmi"
