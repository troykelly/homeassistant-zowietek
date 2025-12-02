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
    """Mock ZowietekClient for coordinator testing."""
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
        # Note: System data comes from async_get_sys_attr_info
        # Falls back to NDI config's machinename if sys_attr unavailable
        mock_zowietek_client.async_get_input_signal.assert_called_once()
        mock_zowietek_client.async_get_output_info.assert_called_once()
        mock_zowietek_client.async_get_venc_info.assert_called_once()
        mock_zowietek_client.async_get_stream_publish_info.assert_called_once()
        mock_zowietek_client.async_get_ndi_config.assert_called_once()
        mock_zowietek_client.async_get_audio_info.assert_called_once()

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
        """Test coordinator populates system info from NDI machinename.

        System info is built from NDI config's machinename since the
        device info endpoint is not available on all firmware.
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # With machinename "ZowieBox-Test", system gets:
        # devicename = "ZowieBox-Test" (full machinename)
        # devicesn = "Test" (part after the dash)
        assert coordinator.data.system["devicesn"] == "Test"
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

        assert coordinator.data.stream["ndi_switch"] == 1
        assert coordinator.data.stream["ndi_name"] == "ZowieBox-Test"


class TestZowietekCoordinatorErrors:
    """Tests for ZowietekCoordinator error handling."""

    async def test_auth_error_raises_config_entry_auth_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test authentication error triggers ConfigEntryAuthFailed.

        Auth errors should always be raised from required endpoints.
        """
        mock_config_entry.add_to_hass(hass)

        # Auth error on required endpoint should raise ConfigEntryAuthFailed
        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekAuthError(
            "Authentication failed"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(ConfigEntryAuthFailed):
            await _refresh_coordinator(coordinator)

    async def test_optional_endpoint_failure_does_not_raise(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test optional endpoint failures are handled gracefully.

        Sys attr and NDI config are optional endpoints that may not be
        supported on all firmware versions. Failures should not cause
        the coordinator to fail.
        """
        mock_config_entry.add_to_hass(hass)

        # Both optional endpoints fail
        mock_zowietek_client.async_get_sys_attr_info.side_effect = ZowietekApiError(
            "param group not support"
        )
        mock_zowietek_client.async_get_ndi_config.side_effect = ZowietekApiError(
            "Endpoint not found"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should still succeed with empty system/ndi data
        assert isinstance(coordinator.data, ZowietekData)
        assert coordinator.data.system == {}  # Optional endpoint failed
        assert "ndi_switch" not in coordinator.data.stream  # NDI not available

    async def test_optional_endpoint_non_dict_returns_empty(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test optional endpoint returning non-dict is handled gracefully."""
        mock_config_entry.add_to_hass(hass)

        # Optional endpoint returns non-dict (e.g., None or list)
        mock_zowietek_client.async_get_sys_attr_info.return_value = None
        mock_zowietek_client.async_get_ndi_config.return_value = ["not", "a", "dict"]

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should succeed with empty data for non-dict responses
        assert isinstance(coordinator.data, ZowietekData)
        assert coordinator.data.system == {}

    async def test_connection_error_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test connection error on required endpoint raises UpdateFailed."""
        mock_config_entry.add_to_hass(hass)

        # Venc info is required - connection error should raise UpdateFailed
        mock_zowietek_client.async_get_venc_info.side_effect = ZowietekConnectionError(
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
        """Test API error on required endpoint raises UpdateFailed."""
        mock_config_entry.add_to_hass(hass)

        # Input signal is required - API error should raise UpdateFailed
        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekApiError("API error")

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

    async def test_partial_api_failure_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_input_signal: dict[str, str | int],
    ) -> None:
        """Test partial API failure (e.g., venc endpoint fails) raises UpdateFailed."""
        mock_config_entry.add_to_hass(hass)

        # Input signal succeeds but venc info fails
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_venc_info.side_effect = ZowietekApiError(
            "Venc endpoint failed"
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
        mock_input_signal: dict[str, str | int],
        mock_output_info: dict[str, str | int],
        mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
        mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
        mock_ndi_config: dict[str, str | int],
        mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
    ) -> None:
        """Test coordinator recovers after connection is restored."""
        mock_config_entry.add_to_hass(hass)

        # First call fails on required endpoint (venc_info)
        mock_zowietek_client.async_get_venc_info.side_effect = ZowietekConnectionError(
            "Connection failed"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

        # Restore connection
        mock_zowietek_client.async_get_venc_info.side_effect = None
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_output_info.return_value = mock_output_info
        mock_zowietek_client.async_get_venc_info.return_value = mock_venc_info
        mock_zowietek_client.async_get_stream_publish_info.return_value = mock_stream_publish_info
        mock_zowietek_client.async_get_ndi_config.return_value = mock_ndi_config
        mock_zowietek_client.async_get_audio_info.return_value = mock_audio_info

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
        """Test coordinator exposes device_id property.

        Device ID is extracted from NDI machinename (part after last dash).
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # With machinename "ZowieBox-Test", devicesn becomes "Test"
        assert coordinator.device_id == "Test"

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
        """Test device_id falls back to config entry unique_id if machinename has no dash."""
        mock_config_entry.add_to_hass(hass)

        # NDI config with machinename that has no dash (can't extract devicesn)
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "switch": 1,
            "machinename": "MyDevice",  # No dash, so no devicesn extracted
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should fall back to config entry unique_id since no devicesn from machinename
        assert coordinator.device_id == "zowiebox-test-12345"

    async def test_device_name_fallback_to_title(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test device_name falls back to config entry title if NDI config not available."""
        mock_config_entry.add_to_hass(hass)

        # NDI config returns empty or no machinename
        mock_zowietek_client.async_get_ndi_config.return_value = {
            "status": "00000",
            "rsp": "succeed",
            "switch": 1,
            # No machinename field
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should fall back to config entry title since no machinename
        assert coordinator.device_name == "Test ZowieBox"


class TestZowietekCoordinatorOptionalEndpointAuthError:
    """Tests for optional endpoint auth error re-raising."""

    async def test_optional_endpoint_auth_error_reraises(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test that auth errors from optional endpoints are re-raised.

        Even optional endpoints should fail fast on auth errors since
        the credentials are invalid for the entire device.
        """
        mock_config_entry.add_to_hass(hass)

        # Auth error on optional endpoint (sys_attr_info) should still raise
        mock_zowietek_client.async_get_sys_attr_info = AsyncMock(
            side_effect=ZowietekAuthError("Authentication failed")
        )
        # Also mock the required ones to be available
        mock_zowietek_client.async_get_dashboard_info = AsyncMock(return_value={})

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(ConfigEntryAuthFailed):
            await _refresh_coordinator(coordinator)


class TestZowietekCoordinatorVencParsing:
    """Tests for venc info parsing edge cases."""

    async def test_venc_empty_list_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test that empty venc list is handled gracefully."""
        mock_config_entry.add_to_hass(hass)

        # Return empty venc list
        mock_zowietek_client.async_get_venc_info.return_value = {"venc": []}

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Video info should have empty/default values when no venc
        assert coordinator.data.video.get("enc_resolution") in (None, "")
        assert coordinator.data.video.get("enc_type") in (None, "")

    async def test_venc_not_list_returns_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test that non-list venc is handled gracefully."""
        mock_config_entry.add_to_hass(hass)

        # Return venc as non-list (e.g., dict or None)
        mock_zowietek_client.async_get_venc_info.return_value = {"venc": None}

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should succeed with empty/default values
        assert isinstance(coordinator.data, ZowietekData)

    async def test_venc_fallback_to_first_channel(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test fallback to first venc channel when no 'main' desc found."""
        mock_config_entry.add_to_hass(hass)

        # Return venc list without "main" desc - should use first channel
        mock_zowietek_client.async_get_venc_info.return_value = {
            "venc": [
                {
                    "venc_chnid": 0,
                    "codec": {"selected_id": 0, "codec_list": ["H.264"]},
                    "bitrate": 8000000,
                    "width": 1280,
                    "height": 720,
                    "framerate": 30,
                    "desc": "sub",  # Not "main"
                },
            ]
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should use first channel values
        assert coordinator.data.video["enc_resolution"] == "1280x720"
        assert coordinator.data.video["enc_framerate"] == 30

    async def test_venc_first_element_not_dict(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test handling when first venc element is not a dict."""
        mock_config_entry.add_to_hass(hass)

        # Return venc list with non-dict first element
        mock_zowietek_client.async_get_venc_info.return_value = {
            "venc": ["not a dict", {"desc": "main"}]
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should handle gracefully (uses second element which has "main")
        assert isinstance(coordinator.data, ZowietekData)

    async def test_venc_first_element_not_dict_no_main(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test handling when first venc element is not a dict and no 'main' exists."""
        mock_config_entry.add_to_hass(hass)

        # Return venc list with non-dict first element and no "main" desc
        mock_zowietek_client.async_get_venc_info.return_value = {"venc": ["not a dict"]}

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should handle gracefully - first element isn't dict so _get_main_encoder returns None
        assert isinstance(coordinator.data, ZowietekData)


class TestZowietekCoordinatorInputSignal:
    """Tests for input signal handling edge cases."""

    async def test_input_signal_with_signal_key(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test handling input signal with 'signal' key instead of 'hdmi_signal'."""
        mock_config_entry.add_to_hass(hass)

        # Return input signal with 'signal' key
        mock_zowietek_client.async_get_input_signal.return_value = {
            "signal": 1,  # Legacy key
            "width": 1920,
            "height": 1080,
            "framerate": 60,
        }

        coordinator = ZowietekCoordinator(hass, mock_config_entry)
        await _refresh_coordinator(coordinator)

        # Should process the signal key
        assert coordinator.data.video.get("input_signal") == 1


class TestZowietekCoordinatorConnectionRecovery:
    """Tests for ZowietekCoordinator connection recovery behavior.

    These tests verify that the coordinator properly handles:
    - Temporary network failures
    - Device reboots (extended unavailability)
    - Automatic recovery when connection is restored
    - Timeout errors
    """

    async def test_timeout_error_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test timeout error on required endpoint raises UpdateFailed.

        Timeout errors are a type of connection error and should result
        in UpdateFailed, marking entities as unavailable.
        """
        from custom_components.zowietek.exceptions import ZowietekTimeoutError

        mock_config_entry.add_to_hass(hass)

        # Timeout on required endpoint should raise UpdateFailed
        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekTimeoutError(
            "Request timed out after 10 seconds"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

    async def test_multiple_consecutive_failures_then_recovery(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_input_signal: dict[str, str | int],
        mock_output_info: dict[str, str | int],
        mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
        mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
        mock_ndi_config: dict[str, str | int],
        mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
    ) -> None:
        """Test coordinator recovers after multiple consecutive failures.

        Simulates a device reboot scenario where the device is unavailable
        for multiple polling cycles before coming back online.
        """
        mock_config_entry.add_to_hass(hass)

        # Configure all calls to fail initially
        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekConnectionError(
            "Connection refused"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        # First failure
        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

        # Second failure
        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

        # Third failure
        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

        # Now restore connection - all endpoints succeed
        mock_zowietek_client.async_get_input_signal.side_effect = None
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_output_info.return_value = mock_output_info
        mock_zowietek_client.async_get_venc_info.return_value = mock_venc_info
        mock_zowietek_client.async_get_stream_publish_info.return_value = mock_stream_publish_info
        mock_zowietek_client.async_get_ndi_config.return_value = mock_ndi_config
        mock_zowietek_client.async_get_audio_info.return_value = mock_audio_info

        # Recovery should succeed
        await _refresh_coordinator(coordinator)

        assert isinstance(coordinator.data, ZowietekData)
        assert coordinator.data.video["enc_resolution"] == "1920x1080"

    async def test_recovery_after_device_reboot(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_input_signal: dict[str, str | int],
        mock_output_info: dict[str, str | int],
        mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
        mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
        mock_ndi_config: dict[str, str | int],
        mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
    ) -> None:
        """Test coordinator handles device reboot scenario.

        During a reboot, the device may:
        1. Close connections abruptly
        2. Be unreachable for several seconds
        3. Come back with all endpoints available

        The coordinator should handle all phases gracefully.
        """
        from custom_components.zowietek.exceptions import ZowietekTimeoutError

        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        # Initial successful fetch
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_output_info.return_value = mock_output_info
        mock_zowietek_client.async_get_venc_info.return_value = mock_venc_info
        mock_zowietek_client.async_get_stream_publish_info.return_value = mock_stream_publish_info
        mock_zowietek_client.async_get_ndi_config.return_value = mock_ndi_config
        mock_zowietek_client.async_get_audio_info.return_value = mock_audio_info

        await _refresh_coordinator(coordinator)
        assert isinstance(coordinator.data, ZowietekData)

        # Simulate reboot - device becomes unreachable
        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekTimeoutError(
            "Connection timed out"
        )

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

        # Device comes back online
        mock_zowietek_client.async_get_input_signal.side_effect = None
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal

        await _refresh_coordinator(coordinator)

        # Should recover with fresh data
        assert isinstance(coordinator.data, ZowietekData)
        assert coordinator.data.video["enc_resolution"] == "1920x1080"

    async def test_auth_error_on_optional_endpoint_during_recovery(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_input_signal: dict[str, str | int],
        mock_output_info: dict[str, str | int],
        mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
        mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
    ) -> None:
        """Test auth error on optional endpoint triggers reauth even during recovery.

        If credentials expire while the device was rebooting, the coordinator
        should detect the auth error and trigger reauthentication.
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        # Setup: device was offline, now coming back with expired credentials
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_output_info.return_value = mock_output_info
        mock_zowietek_client.async_get_venc_info.return_value = mock_venc_info
        mock_zowietek_client.async_get_stream_publish_info.return_value = mock_stream_publish_info

        # Optional endpoint returns auth error (credentials expired during reboot)
        mock_zowietek_client.async_get_ndi_config = AsyncMock(
            side_effect=ZowietekAuthError("Session expired")
        )
        mock_zowietek_client.async_get_audio_info = AsyncMock(return_value={})
        mock_zowietek_client.async_get_sys_attr_info = AsyncMock(return_value={})
        mock_zowietek_client.async_get_dashboard_info = AsyncMock(return_value={})

        with pytest.raises(ConfigEntryAuthFailed):
            await _refresh_coordinator(coordinator)

    async def test_network_interruption_recovery(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_input_signal: dict[str, str | int],
        mock_output_info: dict[str, str | int],
        mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
        mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
        mock_ndi_config: dict[str, str | int],
        mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
    ) -> None:
        """Test recovery from network interruption.

        Network interruptions may cause different error types:
        - Connection refused
        - DNS resolution failure
        - Connection timeout

        The coordinator should handle all these and recover.
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        # Configure successful initial state
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_output_info.return_value = mock_output_info
        mock_zowietek_client.async_get_venc_info.return_value = mock_venc_info
        mock_zowietek_client.async_get_stream_publish_info.return_value = mock_stream_publish_info
        mock_zowietek_client.async_get_ndi_config.return_value = mock_ndi_config
        mock_zowietek_client.async_get_audio_info.return_value = mock_audio_info

        await _refresh_coordinator(coordinator)

        # Network interruption - different error types
        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekConnectionError(
            "Cannot connect to host"
        )

        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)

        # Network restored
        mock_zowietek_client.async_get_input_signal.side_effect = None
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal

        await _refresh_coordinator(coordinator)

        assert isinstance(coordinator.data, ZowietekData)

    async def test_consecutive_failures_count_tracking(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_input_signal: dict[str, str | int],
        mock_output_info: dict[str, str | int],
        mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
        mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
        mock_ndi_config: dict[str, str | int],
        mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
    ) -> None:
        """Test that consecutive failures are tracked for diagnostics.

        The coordinator should track the number of consecutive failures
        to help diagnose persistent connection issues.
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        # All endpoints fail
        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekConnectionError(
            "Connection failed"
        )

        # Track failures
        for i in range(5):
            with pytest.raises(UpdateFailed):
                await _refresh_coordinator(coordinator)

            # Verify consecutive failures count is tracked
            assert coordinator.consecutive_failures == i + 1

        # Recovery resets the counter
        mock_zowietek_client.async_get_input_signal.side_effect = None
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_output_info.return_value = mock_output_info
        mock_zowietek_client.async_get_venc_info.return_value = mock_venc_info
        mock_zowietek_client.async_get_stream_publish_info.return_value = mock_stream_publish_info
        mock_zowietek_client.async_get_ndi_config.return_value = mock_ndi_config
        mock_zowietek_client.async_get_audio_info.return_value = mock_audio_info

        await _refresh_coordinator(coordinator)

        assert coordinator.consecutive_failures == 0

    async def test_error_message_includes_host(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test that error messages include the host for debugging.

        When connection fails, the error message should include the host
        to help identify which device is having issues.
        """
        mock_config_entry.add_to_hass(hass)

        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekConnectionError(
            "Connection refused"
        )

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed) as exc_info:
            await _refresh_coordinator(coordinator)

        # Error message should include the host
        assert "192.168.1.100" in str(exc_info.value)

    async def test_api_error_consecutive_failures_debug_logging(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_input_signal: dict[str, str | int],
        mock_output_info: dict[str, str | int],
        mock_venc_info: dict[str, list[dict[str, str | int | dict[str, str | int | list[str]]]]],
        mock_stream_publish_info: dict[str, list[dict[str, str | int]]],
        mock_ndi_config: dict[str, str | int],
        mock_audio_info: dict[str, str | int | dict[str, str | int | list[str]]],
    ) -> None:
        """Test that consecutive API errors use debug logging after first warning.

        This ensures the ZowietekApiError path (not just ZowietekConnectionError)
        uses debug logging for subsequent failures to avoid log spam.
        """
        mock_config_entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, mock_config_entry)

        # First call succeeds
        mock_zowietek_client.async_get_input_signal.return_value = mock_input_signal
        mock_zowietek_client.async_get_output_info.return_value = mock_output_info
        mock_zowietek_client.async_get_venc_info.return_value = mock_venc_info
        mock_zowietek_client.async_get_stream_publish_info.return_value = mock_stream_publish_info
        mock_zowietek_client.async_get_ndi_config.return_value = mock_ndi_config
        mock_zowietek_client.async_get_audio_info.return_value = mock_audio_info

        await _refresh_coordinator(coordinator)
        assert coordinator.consecutive_failures == 0

        # Now API errors occur (not connection errors) - uses ZowietekApiError catch
        mock_zowietek_client.async_get_input_signal.side_effect = ZowietekApiError(
            "API returned error"
        )

        # First API error - should log warning
        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)
        assert coordinator.consecutive_failures == 1

        # Second API error - should log debug (covers the else branch on line 406)
        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)
        assert coordinator.consecutive_failures == 2

        # Third API error - still debug logging
        with pytest.raises(UpdateFailed):
            await _refresh_coordinator(coordinator)
        assert coordinator.consecutive_failures == 3

    async def test_coordinator_uses_default_scan_interval(
        self,
        hass: HomeAssistant,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator uses DEFAULT_SCAN_INTERVAL when no options set."""
        from custom_components.zowietek.const import DEFAULT_SCAN_INTERVAL

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test ZowieBox",
            data={
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
            unique_id="zowiebox-test-12345",
        )
        entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, entry)

        # Should use default scan interval
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)

    async def test_coordinator_uses_options_scan_interval(
        self,
        hass: HomeAssistant,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator uses scan_interval from entry.options when set."""
        from custom_components.zowietek.const import CONF_SCAN_INTERVAL

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test ZowieBox",
            data={
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
            options={CONF_SCAN_INTERVAL: 60},
            unique_id="zowiebox-test-12345",
        )
        entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, entry)

        # Should use the options scan interval
        assert coordinator.update_interval == timedelta(seconds=60)

    async def test_coordinator_uses_custom_options_scan_interval(
        self,
        hass: HomeAssistant,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test coordinator uses custom scan_interval value from options."""
        from custom_components.zowietek.const import CONF_SCAN_INTERVAL

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test ZowieBox",
            data={
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
            options={CONF_SCAN_INTERVAL: 120},
            unique_id="zowiebox-test-12345",
        )
        entry.add_to_hass(hass)

        coordinator = ZowietekCoordinator(hass, entry)

        # Should use 120 second interval
        assert coordinator.update_interval == timedelta(seconds=120)
