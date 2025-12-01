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
    # System info methods
    client.async_get_system_info = AsyncMock(
        return_value={
            "status": "00000",
            "rsp": "succeed",
            "devicename": "ZowieBox-Test",
            "devicesn": "zowiebox-test-12345",
            "softver": "1.0.0",
        }
    )

    # Video methods
    client.async_get_video_info = AsyncMock(
        return_value={
            "status": "00000",
            "rsp": "succeed",
            "input_source": "hdmi",
            "input_resolution": "1920x1080",
            "input_fps": "60",
        }
    )

    # Audio methods
    client.async_get_audio_info = AsyncMock(
        return_value={
            "status": "00000",
            "rsp": "succeed",
            "audio_source": "hdmi",
            "volume": "80",
        }
    )

    # Stream methods
    client.async_get_stream_info = AsyncMock(
        return_value={
            "status": "00000",
            "rsp": "succeed",
            "switch": 1,  # NDI enabled state
            "machinename": "ZowieBox-Test",
            "publish": [
                {"type": "rtmp", "index": 0, "switch": 0, "url": ""},
                {"type": "srt", "index": 1, "switch": 0, "url": ""},
            ],
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
    coordinator = MagicMock()
    coordinator.device_id = device_id
    coordinator.device_name = device_name
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.data = {
        "system": {
            "devicename": device_name,
            "devicesn": device_id,
            "softver": "1.0.0",
        },
        "video": {
            "input_source": "hdmi",
            "input_resolution": "1920x1080",
            "input_fps": "60",
        },
        "stream": {
            "switch": 1,  # NDI enabled state
            "machinename": device_name,
            "publish": [
                {"type": "rtmp", "index": 0, "switch": 0, "url": ""},
                {"type": "srt", "index": 1, "switch": 0, "url": ""},
            ],
        },
    }
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator fixture."""
    return create_mock_coordinator()
