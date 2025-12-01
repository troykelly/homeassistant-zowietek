"""Fixtures for Zowietek integration tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek.const import DOMAIN

# Auto-use fixture to enable custom component loading for all tests
pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable custom integrations in Home Assistant."""
    yield


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
def mock_system_info() -> dict[str, Any]:
    """Return mock system info response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "devicename": "ZowieBox-Test",
        "devicesn": "zowiebox-test-12345",
        "softver": "1.0.0",
        "hardver": "2.0",
        "mac": "00:11:22:33:44:55",
    }


@pytest.fixture
def mock_video_info() -> dict[str, Any]:
    """Return mock video info response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "input_source": "hdmi",
        "input_resolution": "1920x1080",
        "input_fps": "60",
        "output_resolution": "1920x1080",
        "output_fps": "60",
    }


@pytest.fixture
def mock_stream_info() -> dict[str, Any]:
    """Return mock stream info response.

    The stream data combines publish list (RTMP/SRT) with NDI config.
    NDI uses 'switch' for enabled state, publish entries also use 'switch'.
    """
    return {
        "status": "00000",
        "rsp": "succeed",
        # NDI config fields (from /video group=ndi)
        "switch": 1,  # NDI enabled state
        "machinename": "ZowieBox-Test",
        "mode_id": 1,
        # Publish list (from /stream group=publish)
        "publish": [
            {"type": "rtmp", "index": 0, "switch": 0, "url": ""},
            {"type": "srt", "index": 1, "switch": 0, "url": ""},
        ],
    }


@pytest.fixture
def mock_zowietek_client(
    mock_system_info: dict[str, Any],
    mock_video_info: dict[str, Any],
    mock_stream_info: dict[str, Any],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for testing."""
    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_login = AsyncMock(return_value=True)
        client.async_get_system_info = AsyncMock(return_value=mock_system_info)
        client.async_get_video_info = AsyncMock(return_value=mock_video_info)
        client.async_get_stream_info = AsyncMock(return_value=mock_stream_info)
        client.async_logout = AsyncMock()
        client.close = AsyncMock()
        client.host = "192.168.1.100"
        yield client


def add_coordinator_mocks(client: MagicMock) -> None:
    """Add all coordinator-related mocks to a client mock.

    This ensures the client mock has all methods required by the
    coordinators for data fetching.

    Args:
        client: The mock client to add methods to.
    """
    # Input signal from /video group=hdmi opt=get_input_info
    client.async_get_input_signal = AsyncMock(
        return_value={
            "hdmi_signal": 1,
            "audio_signal": 48000,
            "width": 1920,
            "height": 1080,
            "framerate": 60,
            "desc": "1080p60",
        }
    )

    # Output info from /video group=hdmi opt=get_output_info
    client.async_get_output_info = AsyncMock(
        return_value={
            "switch": 1,
            "format": "1080p60",
            "audio_switch": 1,
            "loop_out_switch": 0,
        }
    )

    # Venc info from /video group=venc
    client.async_get_venc_info = AsyncMock(
        return_value={
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
                        "codec_list": ["H.264", "H.265", "MJPEG"],
                    },
                    "bitrate": 1000000,
                    "width": 1280,
                    "height": 720,
                    "framerate": 60,
                    "desc": "sub",
                },
            ],
        }
    )

    # Stream publish info from /stream group=publish
    client.async_get_stream_publish_info = AsyncMock(
        return_value={
            "publish": [
                {"type": "rtmp", "index": 0, "switch": 1, "url": "rtmp://test"},
                {"type": "srt", "index": 1, "switch": 0, "url": ""},
            ],
        }
    )

    # NDI config from /video group=ndi
    client.async_get_ndi_config = AsyncMock(
        return_value={
            "activate": 1,
            "switch": 1,
            "mode_id": 1,
            "machinename": "ZowieBox-Test",
            "groups": "Public",
        }
    )

    # Audio info from /audio group=all
    client.async_get_audio_info = AsyncMock(
        return_value={
            "switch": 1,
            "ai_type": {
                "selected_id": 0,
                "ai_type_list": ["LINE IN", "Internal MIC", "HDMI IN", "USB IN"],
            },
            "volume": 100,
        }
    )

    # Legacy methods (for backward compatibility with some tests)
    client.async_get_video_info = AsyncMock(
        return_value={
            "status": "00000",
            "rsp": "succeed",
            "input_source": "hdmi",
            "input_resolution": "1920x1080",
            "input_fps": "60",
        }
    )

    # Network methods
    client.async_get_network_info = AsyncMock(
        return_value={
            "status": "00000",
            "rsp": "succeed",
            "ip": "192.168.1.100",
            "netmask": "255.255.255.0",
            "gateway": "192.168.1.1",
        }
    )

    # Write methods for number entities
    client.async_set_audio_volume = AsyncMock()
    client.async_set_encoder_bitrate = AsyncMock()


def setup_mock_zowietek_client(
    client: MagicMock,
    system_info: dict[str, Any] | None = None,
) -> MagicMock:
    """Setup a mock ZowietekClient with all required mocks for testing.

    This is the recommended way to setup a mock ZowietekClient when using
    patch("custom_components.zowietek.ZowietekClient", autospec=True).

    Args:
        client: The mock client to setup (typically mock_client_class.return_value).
        system_info: Optional system info dict (defaults to basic test device info).

    Returns:
        The configured mock client.

    Example:
        with patch("custom_components.zowietek.ZowietekClient", autospec=True) as mock_cls:
            client = setup_mock_zowietek_client(mock_cls.return_value)
            # Now client has all required mocks
    """
    if system_info is None:
        system_info = {
            "status": "00000",
            "rsp": "succeed",
            "devicename": "ZowieBox-Test",
            "devicesn": "zowiebox-test-12345",
            "softver": "1.0.0",
        }

    # Basic client methods
    client.async_login = AsyncMock(return_value=True)
    client.async_get_system_info = AsyncMock(return_value=system_info)
    client.async_logout = AsyncMock()
    client.close = AsyncMock()
    client.host = "192.168.1.100"

    # Add all coordinator-related mocks
    add_coordinator_mocks(client)

    return client


@pytest.fixture
def mock_zowietek_client_init(
    mock_system_info: dict[str, Any],
    mock_video_info: dict[str, Any],
    mock_stream_info: dict[str, Any],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for __init__.py testing."""
    with patch("custom_components.zowietek.ZowietekClient", autospec=True) as mock_client_class:
        client = mock_client_class.return_value
        client.async_login = AsyncMock(return_value=True)
        client.async_get_system_info = AsyncMock(return_value=mock_system_info)
        client.async_get_video_info = AsyncMock(return_value=mock_video_info)
        client.async_get_stream_info = AsyncMock(return_value=mock_stream_info)
        client.async_logout = AsyncMock()
        client.close = AsyncMock()
        client.host = "192.168.1.100"
        # Add coordinator-related mocks
        add_coordinator_mocks(client)
        yield client


@pytest.fixture
def mock_aiohttp_session() -> Generator[MagicMock]:
    """Mock aiohttp ClientSession."""
    with patch("aiohttp.ClientSession", autospec=True) as mock_session:
        session = mock_session.return_value
        session.closed = False
        session.close = AsyncMock()
        yield session


def create_mock_coordinator(
    device_id: str = "zowiebox-test-12345",
    device_name: str = "ZowieBox-Test",
) -> MagicMock:
    """Create a mock coordinator with required attributes.

    Args:
        device_id: The device ID for the coordinator.
        device_name: The device name for the coordinator.

    Returns:
        A MagicMock configured as a coordinator.
    """
    from custom_components.zowietek.models import ZowietekData

    coordinator = MagicMock()
    coordinator.device_id = device_id
    coordinator.device_name = device_name
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.data = ZowietekData(
        system={
            "devicename": device_name,
            "devicesn": device_id,
        },
        video={
            "input": {
                "hdmi_signal": 1,
                "width": 1920,
                "height": 1080,
                "framerate": 60,
            },
            "output": {
                "format": "1080p60",
            },
            "enc_resolution": "1920x1080",
            "enc_framerate": 60,
            "enc_bitrate": 12000000,
            "enc_type": "H.264",
            "output_format": "1080p60",
        },
        audio={
            "switch": 1,
            "volume": 100,
        },
        stream={
            "ndi_switch": 1,
            "ndi_name": device_name,
            "ndi_mode_id": 1,
            "publish": [
                {"type": "rtmp", "index": 0, "switch": 1, "url": "rtmp://test"},
                {"type": "srt", "index": 1, "switch": 0, "url": ""},
            ],
        },
        network={},
    )
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator fixture."""
    return create_mock_coordinator()
