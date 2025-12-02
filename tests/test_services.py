"""Tests for Zowietek custom services."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek.const import DOMAIN
from custom_components.zowietek.services import (
    ATTR_DEVICE_ID,
    ATTR_GROUP,
    ATTR_KEY,
    ATTR_LATENCY,
    ATTR_NAME,
    ATTR_PASSPHRASE,
    ATTR_PORT,
    ATTR_URL,
    SERVICE_SET_NDI_SETTINGS,
    SERVICE_SET_RTMP_URL,
    SERVICE_SET_SRT_SETTINGS,
)

from .conftest import add_coordinator_mocks

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_config_entry_for_services() -> MockConfigEntry:
    """Create a mock config entry for service tests."""
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


async def setup_integration_with_mocked_client(
    hass: HomeAssistant,
    entry: MockConfigEntry,
) -> MagicMock:
    """Set up the integration with a mocked client.

    Args:
        hass: Home Assistant instance.
        entry: Mock config entry.

    Returns:
        The mocked client instance.
    """
    with patch(
        "custom_components.zowietek.coordinator.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100"
        client.close = AsyncMock()

        # Add sys_attr mock for device info
        client.async_get_sys_attr_info = AsyncMock(
            return_value={
                "SN": "zowiebox-test-12345",
                "device_name": "ZowieBox-Test",
                "firmware_version": "1.0.0",
                "hardware_version": "2.0",
                "model": "ZowieBox",
                "manufacturer": "Zowietek",
            }
        )

        # Add dashboard info mock
        client.async_get_dashboard_info = AsyncMock(
            return_value={
                "persistent_time": "01:23:45",
                "device_strat_time": "2024-01-01 00:00:00",
                "cpu_temp": 45.0,
                "cpu_payload": 25.0,
            }
        )

        # Add all coordinator mocks
        add_coordinator_mocks(client)

        # Add service-specific mocks
        client.async_set_ndi_settings = AsyncMock()
        client.async_set_rtmp_url = AsyncMock()
        client.async_set_srt_settings = AsyncMock()

        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        return client


class TestServiceRegistration:
    """Tests for service registration."""

    async def test_services_registered_on_setup(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test that services are registered when the integration is set up."""
        await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        # Verify services are registered
        assert hass.services.has_service(DOMAIN, SERVICE_SET_NDI_SETTINGS)
        assert hass.services.has_service(DOMAIN, SERVICE_SET_RTMP_URL)
        assert hass.services.has_service(DOMAIN, SERVICE_SET_SRT_SETTINGS)

    async def test_services_unregistered_on_unload(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test that services are unregistered when the last entry is unloaded."""
        await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        # Verify services exist
        assert hass.services.has_service(DOMAIN, SERVICE_SET_NDI_SETTINGS)
        assert hass.services.has_service(DOMAIN, SERVICE_SET_RTMP_URL)
        assert hass.services.has_service(DOMAIN, SERVICE_SET_SRT_SETTINGS)

        # Unload the entry
        await hass.config_entries.async_unload(mock_config_entry_for_services.entry_id)
        await hass.async_block_till_done()

        # Services should be unregistered when last entry is unloaded
        assert not hass.services.has_service(DOMAIN, SERVICE_SET_NDI_SETTINGS)
        assert not hass.services.has_service(DOMAIN, SERVICE_SET_RTMP_URL)
        assert not hass.services.has_service(DOMAIN, SERVICE_SET_SRT_SETTINGS)


class TestSetNdiSettingsService:
    """Tests for set_ndi_settings service."""

    async def test_set_ndi_settings_success(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test successfully setting NDI settings."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        # Get the device ID from the device registry
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        # Call the service
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_NDI_SETTINGS,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_NAME: "MyNDISource",
                ATTR_GROUP: "ProductionGroup",
            },
            blocking=True,
        )

        # Verify API was called correctly
        client.async_set_ndi_settings.assert_called_once_with(
            name="MyNDISource",
            group="ProductionGroup",
        )

    async def test_set_ndi_settings_name_only(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test setting only the NDI name without group."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        # Call the service with only name
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_NDI_SETTINGS,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_NAME: "MyNDISource",
            },
            blocking=True,
        )

        # Verify API was called with name and None for group
        client.async_set_ndi_settings.assert_called_once_with(
            name="MyNDISource",
            group=None,
        )

    async def test_set_ndi_settings_invalid_device(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test setting NDI settings with invalid device ID."""
        await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        # Call with invalid device ID
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SET_NDI_SETTINGS,
                {
                    ATTR_DEVICE_ID: "invalid_device_id",
                    ATTR_NAME: "MyNDISource",
                },
                blocking=True,
            )

    async def test_set_ndi_settings_api_error(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test handling API errors when setting NDI settings."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        # Make the API call fail
        from custom_components.zowietek.exceptions import ZowietekApiError

        client.async_set_ndi_settings.side_effect = ZowietekApiError("API Error")

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SET_NDI_SETTINGS,
                {
                    ATTR_DEVICE_ID: device.id,
                    ATTR_NAME: "MyNDISource",
                },
                blocking=True,
            )


class TestSetRtmpUrlService:
    """Tests for set_rtmp_url service."""

    async def test_set_rtmp_url_success(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test successfully setting RTMP URL."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        # Call the service
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_RTMP_URL,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_URL: "rtmp://live.example.com/live",
                ATTR_KEY: "stream_key_123",
            },
            blocking=True,
        )

        # Verify API was called correctly
        client.async_set_rtmp_url.assert_called_once_with(
            url="rtmp://live.example.com/live",
            key="stream_key_123",
        )

    async def test_set_rtmp_url_without_key(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test setting RTMP URL without stream key."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        # Call the service without key
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_RTMP_URL,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_URL: "rtmp://live.example.com/live",
            },
            blocking=True,
        )

        # Verify API was called with None for key
        client.async_set_rtmp_url.assert_called_once_with(
            url="rtmp://live.example.com/live",
            key=None,
        )

    async def test_set_rtmp_url_invalid_device(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test setting RTMP URL with invalid device ID."""
        await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SET_RTMP_URL,
                {
                    ATTR_DEVICE_ID: "invalid_device_id",
                    ATTR_URL: "rtmp://live.example.com/live",
                },
                blocking=True,
            )

    async def test_set_rtmp_url_api_error(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test handling API errors when setting RTMP URL."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        from custom_components.zowietek.exceptions import ZowietekApiError

        client.async_set_rtmp_url.side_effect = ZowietekApiError("API Error")

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SET_RTMP_URL,
                {
                    ATTR_DEVICE_ID: device.id,
                    ATTR_URL: "rtmp://live.example.com/live",
                },
                blocking=True,
            )


class TestSetSrtSettingsService:
    """Tests for set_srt_settings service."""

    async def test_set_srt_settings_success(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test successfully setting SRT settings."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        # Call the service
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SRT_SETTINGS,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_PORT: 9000,
                ATTR_LATENCY: 120,
                ATTR_PASSPHRASE: "mysecretkey",
            },
            blocking=True,
        )

        # Verify API was called correctly
        client.async_set_srt_settings.assert_called_once_with(
            port=9000,
            latency=120,
            passphrase="mysecretkey",
        )

    async def test_set_srt_settings_partial(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test setting only some SRT settings."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        # Call the service with only port
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SRT_SETTINGS,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_PORT: 9000,
            },
            blocking=True,
        )

        # Verify API was called with None for optional params
        client.async_set_srt_settings.assert_called_once_with(
            port=9000,
            latency=None,
            passphrase=None,
        )

    async def test_set_srt_settings_invalid_device(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test setting SRT settings with invalid device ID."""
        await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SET_SRT_SETTINGS,
                {
                    ATTR_DEVICE_ID: "invalid_device_id",
                    ATTR_PORT: 9000,
                },
                blocking=True,
            )

    async def test_set_srt_settings_api_error(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test handling API errors when setting SRT settings."""
        client = await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        from custom_components.zowietek.exceptions import ZowietekApiError

        client.async_set_srt_settings.side_effect = ZowietekApiError("API Error")

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SET_SRT_SETTINGS,
                {
                    ATTR_DEVICE_ID: device.id,
                    ATTR_PORT: 9000,
                },
                blocking=True,
            )


class TestCoordinatorRefresh:
    """Tests for coordinator refresh after service calls."""

    async def test_ndi_settings_triggers_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test that setting NDI settings triggers a coordinator refresh."""
        await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        # Get the coordinator and track refresh calls
        coordinator = mock_config_entry_for_services.runtime_data
        coordinator.async_request_refresh = AsyncMock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_NDI_SETTINGS,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_NAME: "MyNDISource",
            },
            blocking=True,
        )

        # Verify refresh was requested
        coordinator.async_request_refresh.assert_called_once()

    async def test_rtmp_url_triggers_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test that setting RTMP URL triggers a coordinator refresh."""
        await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        coordinator = mock_config_entry_for_services.runtime_data
        coordinator.async_request_refresh = AsyncMock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_RTMP_URL,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_URL: "rtmp://live.example.com/live",
            },
            blocking=True,
        )

        coordinator.async_request_refresh.assert_called_once()

    async def test_srt_settings_triggers_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry_for_services: MockConfigEntry,
    ) -> None:
        """Test that setting SRT settings triggers a coordinator refresh."""
        await setup_integration_with_mocked_client(
            hass,
            mock_config_entry_for_services,
        )

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, "zowiebox-test-12345")})
        assert device is not None

        coordinator = mock_config_entry_for_services.runtime_data
        coordinator.async_request_refresh = AsyncMock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SRT_SETTINGS,
            {
                ATTR_DEVICE_ID: device.id,
                ATTR_PORT: 9000,
            },
            blocking=True,
        )

        coordinator.async_request_refresh.assert_called_once()
