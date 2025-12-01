"""Tests for the Zowietek integration setup and unload."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.zowietek.const import DOMAIN
from custom_components.zowietek.coordinator import ZowietekCoordinator
from custom_components.zowietek.exceptions import (
    ZowietekAuthError,
    ZowietekConnectionError,
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
    """Mock ZowietekClient for integration testing."""
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


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    async def test_setup_entry_successful(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test successful setup of config entry."""
        mock_config_entry.add_to_hass(hass)

        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True

    async def test_setup_entry_creates_coordinator(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setup creates coordinator and stores in runtime_data."""
        mock_config_entry.add_to_hass(hass)

        await async_setup_entry(hass, mock_config_entry)

        assert mock_config_entry.runtime_data is not None
        assert isinstance(mock_config_entry.runtime_data, ZowietekCoordinator)

    async def test_setup_entry_performs_first_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setup performs first data refresh."""
        mock_config_entry.add_to_hass(hass)

        await async_setup_entry(hass, mock_config_entry)

        # Verify API was called during first refresh
        mock_zowietek_client.async_get_video_info.assert_called()

    async def test_setup_entry_forwards_to_platforms(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setup forwards to all platforms."""
        mock_config_entry.add_to_hass(hass)

        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ) as mock_forward:
            await async_setup_entry(hass, mock_config_entry)

            mock_forward.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_setup_entry_raises_auth_failed_on_auth_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setup raises ConfigEntryAuthFailed on authentication error."""
        mock_config_entry.add_to_hass(hass)

        # Simulate auth error during first refresh
        mock_zowietek_client.async_get_video_info.side_effect = ZowietekAuthError(
            "Authentication failed"
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, mock_config_entry)

    async def test_setup_entry_raises_not_ready_on_connection_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test setup raises ConfigEntryNotReady on connection error."""
        mock_config_entry.add_to_hass(hass)

        # Simulate connection error during first refresh
        mock_zowietek_client.async_get_video_info.side_effect = ZowietekConnectionError(
            "Connection failed"
        )

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    async def test_unload_entry_successful(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test successful unload of config entry."""
        mock_config_entry.add_to_hass(hass)

        await async_setup_entry(hass, mock_config_entry)
        result = await async_unload_entry(hass, mock_config_entry)

        assert result is True

    async def test_unload_entry_unloads_platforms(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test unload unloads all platforms."""
        mock_config_entry.add_to_hass(hass)

        await async_setup_entry(hass, mock_config_entry)

        with patch.object(
            hass.config_entries, "async_unload_platforms", new_callable=AsyncMock
        ) as mock_unload:
            mock_unload.return_value = True
            await async_unload_entry(hass, mock_config_entry)

            mock_unload.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_unload_entry_closes_client(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test unload closes the API client session."""
        mock_config_entry.add_to_hass(hass)

        await async_setup_entry(hass, mock_config_entry)
        await async_unload_entry(hass, mock_config_entry)

        # Verify client was closed
        mock_zowietek_client.close.assert_called_once()


class TestSetupUnloadCycle:
    """Tests for setup -> unload -> setup cycle."""

    async def test_setup_unload_setup_cycle(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test integration can be setup, unloaded, and setup again."""
        mock_config_entry.add_to_hass(hass)

        # First setup
        result1 = await async_setup_entry(hass, mock_config_entry)
        assert result1 is True

        # Unload
        unload_result = await async_unload_entry(hass, mock_config_entry)
        assert unload_result is True

        # Second setup
        result2 = await async_setup_entry(hass, mock_config_entry)
        assert result2 is True


class TestPlatforms:
    """Tests for platform configuration."""

    def test_platforms_defined(self) -> None:
        """Test PLATFORMS constant is defined with expected platforms."""
        from homeassistant.const import Platform

        assert PLATFORMS is not None
        assert len(PLATFORMS) > 0
        # At minimum, we should have sensor platform
        assert Platform.SENSOR in PLATFORMS

    def test_platforms_contains_expected_types(self) -> None:
        """Test PLATFORMS contains expected platform types."""
        from homeassistant.const import Platform

        # These are the platforms we expect to support based on issue #16
        expected_platforms = [
            Platform.SENSOR,
            Platform.BINARY_SENSOR,
            Platform.SWITCH,
            Platform.BUTTON,
            Platform.SELECT,
        ]

        for platform in expected_platforms:
            assert platform in PLATFORMS, f"Missing platform: {platform}"
