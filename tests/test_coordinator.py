"""Tests for the Zowietek Data Update Coordinator."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek.const import DOMAIN
from custom_components.zowietek.coordinator import ZowietekCoordinator
from custom_components.zowietek.exceptions import (
    ZowietekApiError,
    ZowietekAuthError,
    ZowietekConnectionError,
)
from custom_components.zowietek.models import ZowietekData

if TYPE_CHECKING:
    from collections.abc import Generator


async def _refresh_coordinator(coordinator: ZowietekCoordinator) -> None:
    """Helper to refresh coordinator and handle UpdateFailed properly.

    Uses _async_update_data directly to avoid config entry state checks
    that async_config_entry_first_refresh requires.
    """
    coordinator.data = await coordinator._async_update_data()


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
            {
                "type": "srt",
                "enable": 0,
                "url": "",
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
        "ndi_name": "ZowieBox-Test",
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
    """Mock ZowietekClient for coordinator testing."""
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


class TestZowietekCoordinatorInit:
    """Tests for ZowietekCoordinator initialization."""

    async def test_coordinator_init(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator initializes correctly."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        assert coordinator.name == DOMAIN
        assert coordinator.config_entry == mock_config_entry
        assert coordinator.update_interval == timedelta(seconds=30)

    async def test_coordinator_has_client(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator creates API client."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        assert coordinator.client is not None


class TestZowietekCoordinatorUpdate:
    """Tests for ZowietekCoordinator data updates."""

    async def test_update_fetches_all_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator fetches all data types."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Verify all API methods were called
        mock_zowietek_client.async_get_device_info.assert_called_once()
        mock_zowietek_client.async_get_video_info.assert_called_once()
        mock_zowietek_client.async_get_input_signal.assert_called_once()
        mock_zowietek_client.async_get_output_info.assert_called_once()
        mock_zowietek_client.async_get_stream_publish_info.assert_called_once()
        mock_zowietek_client.async_get_ndi_config.assert_called_once()

    async def test_update_returns_zowietek_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator returns ZowietekData dataclass."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        assert isinstance(coordinator.data, ZowietekData)

    async def test_update_populates_system_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_device_info: dict[str, str],
    ) -> None:
        """Test coordinator populates system info from device."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        assert coordinator.data.system["devicesn"] == "zowiebox-test-12345"
        assert coordinator.data.system["devicename"] == "ZowieBox-Test"

    async def test_update_populates_video_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator populates video info from device."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        assert coordinator.data.video["enc_resolution"] == "1920x1080"
        assert coordinator.data.video["enc_framerate"] == 60

    async def test_update_populates_stream_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator populates stream info from device."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        assert coordinator.data.stream["ndi_enable"] == 1
        assert coordinator.data.stream["ndi_name"] == "ZowieBox-Test"


class TestZowietekCoordinatorErrors:
    """Tests for ZowietekCoordinator error handling."""

    async def test_auth_error_raises_config_entry_auth_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test authentication error triggers ConfigEntryAuthFailed."""
        mock_config_entry.add_to_hass(hass)

        mock_zowietek_client.async_get_device_info.side_effect = ZowietekAuthError(
            "Authentication failed"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(ConfigEntryAuthFailed):
            await _refresh_coordinator(coordinator)

    async def test_connection_error_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test connection error raises UpdateFailed."""
        mock_config_entry.add_to_hass(hass)

        mock_zowietek_client.async_get_device_info.side_effect = ZowietekConnectionError(
            "Connection failed"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

    async def test_api_error_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test API error raises UpdateFailed."""
        mock_config_entry.add_to_hass(hass)

        mock_zowietek_client.async_get_device_info.side_effect = ZowietekApiError("API error")

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

    async def test_partial_api_failure_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_device_info: dict[str, str],
    ) -> None:
        """Test partial API failure (e.g., video endpoint fails) raises UpdateFailed."""
        mock_config_entry.add_to_hass(hass)

        # Device info succeeds but video info fails
        mock_zowietek_client.async_get_device_info.return_value = mock_device_info
        mock_zowietek_client.async_get_video_info.side_effect = ZowietekApiError(
            "Video endpoint failed"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)


class TestZowietekCoordinatorRecovery:
    """Tests for ZowietekCoordinator recovery scenarios."""

    async def test_recovery_after_connection_restored(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_device_info: dict[str, str],
        mock_video_info: dict[str, str | int],
        mock_input_signal: dict[str, str | int],
        mock_output_info: dict[str, str | int],
        mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
        mock_ndi_config: dict[str, str | int],
    ) -> None:
        """Test coordinator recovers after connection is restored."""
        mock_config_entry.add_to_hass(hass)

        # First call fails
        mock_zowietek_client.async_get_device_info.side_effect = ZowietekConnectionError(
            "Connection failed"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

        # Restore connection
        mock_zowietek_client.async_get_device_info.side_effect = None
        mock_zowietek_client.async_get_device_info.return_value = mock_device_info
        mock_zowietek_client.async_get_video_info.return_value = mock_video_info
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_output_info.return_value = mock_output_info
        mock_zowietek_client.async_get_stream_publish_info.return_value = mock_stream_publish_info
        mock_zowietek_client.async_get_ndi_config.return_value = mock_ndi_config

        # Second refresh should succeed
        await _refresh_coordinator(coordinator)

        assert isinstance(coordinator.data, ZowietekData)


class TestZowietekCoordinatorParallelFetch:
    """Tests for ZowietekCoordinator parallel data fetching."""

    async def test_parallel_fetch_performance(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test that data fetching happens in parallel for better performance."""
        mock_config_entry.add_to_hass(hass)

        # Track call order with timestamps
        call_times: list[float] = []

        async def record_call(*args: object, **kwargs: object) -> dict[str, str]:
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)  # Small delay to detect sequential vs parallel
            return {"status": "00000", "rsp": "succeed"}

        mock_zowietek_client.async_get_device_info.side_effect = record_call
        mock_zowietek_client.async_get_video_info.side_effect = record_call
        mock_zowietek_client.async_get_input_signal.side_effect = record_call
        mock_zowietek_client.async_get_output_info.side_effect = record_call
        mock_zowietek_client.async_get_stream_publish_info.side_effect = lambda: {"publish": []}
        mock_zowietek_client.async_get_ndi_config.side_effect = record_call

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # If calls were sequential, they'd be spaced ~0.01s apart each
        # If parallel, they should all start at approximately the same time
        # With 5 parallel calls each taking 0.01s, sequential would take ~0.05s
        # Parallel should be close to 0.01s
        if len(call_times) >= 2:
            time_spread = max(call_times) - min(call_times)
            # Allow some tolerance, but calls should start within 0.02s of each other
            assert time_spread < 0.03, f"Calls not parallel, time spread: {time_spread}"


class TestZowietekCoordinatorDeviceInfo:
    """Tests for device information properties on coordinator."""

    async def test_device_id_property(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator exposes device_id property."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        assert coordinator.device_id == "zowiebox-test-12345"

    async def test_device_name_property(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator exposes device_name property."""
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        assert coordinator.device_name == "ZowieBox-Test"

    async def test_device_id_fallback_to_unique_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_id falls back to config entry unique_id if not in data."""
        mock_config_entry.add_to_hass(hass)

        # Device info without serial number
        mock_zowietek_client.async_get_device_info.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "devicename": "ZowieBox-Test",
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should fall back to config entry unique_id
        assert coordinator.device_id == "zowiebox-test-12345"

    async def test_device_name_fallback_to_title(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_name falls back to config entry title if not in data."""
        mock_config_entry.add_to_hass(hass)

        # Device info without device name
        mock_zowietek_client.async_get_device_info.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "devicesn": "zowiebox-test-12345",
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should fall back to config entry title
        assert coordinator.device_name == "Test ZowieBox"
