"""Tests for Zowietek diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.zowietek.const import DOMAIN
from custom_components.zowietek.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)
from custom_components.zowietek.models import ZowietekData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from custom_components.zowietek.coordinator import ZowietekCoordinator


@pytest.fixture
def mock_coordinator_data() -> ZowietekData:
    """Create mock coordinator data for testing."""
    return ZowietekData(
        system={
            "SN": "ABC123456789",
            "firmware_version": "2.0.0.12",
            "hardware_version": "1.0.0",
            "model": "ZowieBox",
            "manufacturer": "Zowietek",
            "device_name": "TestDevice",
            "password": "secret123",
            "psw": "secret456",
        },
        video={
            "enc_type": "H.264",
            "enc_bitrate": 12000000,
            "enc_resolution": "1920x1080",
            "enc_framerate": 60,
        },
        audio={
            "volume": 75,
            "sample_rate": 48000,
        },
        stream={
            "ndi_enable": 1,
            "ndi_name": "ZowieBox-Test",
            "publish": [
                {"type": "rtmp", "switch": 0, "url": "rtmp://example.com/live"},
                {"type": "srt", "switch": 1, "url": "srt://example.com:1234"},
            ],
        },
        network={
            "ip_address": "192.168.1.100",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "gateway": "192.168.1.1",
        },
        dashboard={
            "persistent_time": "12:34:56",
            "cpu_temp": 45.5,
            "cpu_payload": 25.0,
        },
        streamplay={
            "sources": [],
        },
        decoder_status={
            "state": 0,
        },
        ndi_sources=[],
        run_status={
            "status": 1,
        },
    )


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.domain = DOMAIN
    entry.unique_id = "test_device_123"
    entry.entry_id = "entry_123"
    entry.data = {
        "host": "http://192.168.1.100",
        "username": "admin",
        "password": "supersecret",
    }
    entry.options = {
        "scan_interval": 30,
    }
    entry.as_dict = MagicMock(
        return_value={
            "entry_id": "entry_123",
            "domain": DOMAIN,
            "unique_id": "test_device_123",
            "data": {
                "host": "http://192.168.1.100",
                "username": "admin",
                "password": "supersecret",
            },
            "options": {
                "scan_interval": 30,
            },
        }
    )
    return entry


@pytest.fixture
def mock_coordinator(
    mock_config_entry: ConfigEntry,
    mock_coordinator_data: ZowietekData,
) -> ZowietekCoordinator:
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_coordinator_data
    coordinator.config_entry = mock_config_entry
    coordinator.last_update_success = True
    coordinator.consecutive_failures = 0
    return coordinator


class TestDiagnosticsRedaction:
    """Test that sensitive data is redacted."""

    def test_redact_set_contains_password(self) -> None:
        """Test that password is in the redaction set."""
        assert "password" in TO_REDACT

    def test_redact_set_contains_psw(self) -> None:
        """Test that psw (API field) is in the redaction set."""
        assert "psw" in TO_REDACT

    def test_redact_set_contains_serial_number(self) -> None:
        """Test that serial number variations are in the redaction set."""
        assert "SN" in TO_REDACT
        assert "serial_number" in TO_REDACT

    def test_redact_set_contains_mac_address(self) -> None:
        """Test that mac address is in the redaction set."""
        assert "mac_address" in TO_REDACT


class TestAsyncGetConfigEntryDiagnostics:
    """Test the async_get_config_entry_diagnostics function."""

    @pytest.mark.asyncio
    async def test_returns_dict(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that diagnostics returns a dictionary."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_contains_config_entry_section(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that diagnostics contains config entry data."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "config_entry" in result

    @pytest.mark.asyncio
    async def test_contains_device_data_section(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that diagnostics contains device data."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "device_data" in result

    @pytest.mark.asyncio
    async def test_device_data_contains_all_categories(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that device data includes all data categories."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        device_data = result["device_data"]
        assert "system" in device_data
        assert "video" in device_data
        assert "audio" in device_data
        assert "stream" in device_data
        assert "network" in device_data
        assert "dashboard" in device_data

    @pytest.mark.asyncio
    async def test_password_is_redacted_in_config_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that password is redacted in config entry."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        config_data = result["config_entry"]["data"]
        assert config_data["password"] == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_password_is_redacted_in_device_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that password fields are redacted in device data."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        system_data = result["device_data"]["system"]
        assert system_data.get("password") == "**REDACTED**"
        assert system_data.get("psw") == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_serial_number_is_redacted(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that serial number is redacted."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        system_data = result["device_data"]["system"]
        assert system_data.get("SN") == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_mac_address_is_redacted(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that MAC address is redacted."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        network_data = result["device_data"]["network"]
        assert network_data.get("mac_address") == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_contains_coordinator_status(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that diagnostics contains coordinator status."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "coordinator" in result
        assert "last_update_success" in result["coordinator"]
        assert "consecutive_failures" in result["coordinator"]

    @pytest.mark.asyncio
    async def test_non_sensitive_data_not_redacted(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that non-sensitive data is preserved."""
        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Check that non-sensitive data is preserved
        system_data = result["device_data"]["system"]
        assert system_data.get("firmware_version") == "2.0.0.12"
        assert system_data.get("model") == "ZowieBox"

        video_data = result["device_data"]["video"]
        assert video_data.get("enc_type") == "H.264"
        assert video_data.get("enc_bitrate") == 12000000

    @pytest.mark.asyncio
    async def test_handles_missing_coordinator_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
    ) -> None:
        """Test handling when coordinator has no data."""
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.last_update_success = False
        coordinator.consecutive_failures = 5
        mock_config_entry.runtime_data = coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "device_data" in result
        assert result["device_data"] is None or result["device_data"] == {}

    @pytest.mark.asyncio
    async def test_output_is_valid_for_json_serialization(
        self,
        hass: HomeAssistant,
        mock_config_entry: ConfigEntry,
        mock_coordinator: ZowietekCoordinator,
    ) -> None:
        """Test that output can be serialized to JSON."""
        import json

        mock_config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Should not raise an exception
        json_output = json.dumps(result)
        assert isinstance(json_output, str)
        assert len(json_output) > 0
