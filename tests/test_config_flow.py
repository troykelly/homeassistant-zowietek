"""Tests for Zowietek config flow."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.zowietek.const import DOMAIN
from custom_components.zowietek.discovery import DiscoveredDevice

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.zowietek.async_setup_entry",
        return_value=True,
        create=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_discovery_no_devices() -> Generator[AsyncMock]:
    """Mock discovery returning no devices."""
    with patch(
        "custom_components.zowietek.config_flow.async_discover_devices",
        return_value=[],
    ) as mock_discover:
        yield mock_discover


@pytest.fixture
def mock_discovery_one_device() -> Generator[AsyncMock]:
    """Mock discovery returning one device."""
    device = DiscoveredDevice(
        ip="192.168.1.100",
        web_port=80,
        device_sn="ZBOX-ABC123",
        device_name="ZowieBox-Office",
        product_id=2,
        workmode_id=1,
    )
    with patch(
        "custom_components.zowietek.config_flow.async_discover_devices",
        return_value=[device],
    ) as mock_discover:
        yield mock_discover


@pytest.fixture
def mock_discovery_multiple_devices() -> Generator[AsyncMock]:
    """Mock discovery returning multiple devices."""
    devices = [
        DiscoveredDevice(
            ip="192.168.1.100",
            web_port=80,
            device_sn="ZBOX-ABC123",
            device_name="ZowieBox-Office",
            product_id=2,
            workmode_id=1,
        ),
        DiscoveredDevice(
            ip="192.168.1.101",
            web_port=80,
            device_sn="ZBOX-DEF456",
            device_name="ZowieBox-Studio",
            product_id=2,
            workmode_id=1,
        ),
    ]
    with patch(
        "custom_components.zowietek.config_flow.async_discover_devices",
        return_value=devices,
    ) as mock_discover:
        yield mock_discover


@pytest.fixture
def mock_discovery_error() -> Generator[AsyncMock]:
    """Mock discovery raising an error."""
    with patch(
        "custom_components.zowietek.config_flow.async_discover_devices",
        side_effect=OSError("Network error"),
    ) as mock_discover:
        yield mock_discover


@pytest.fixture
def mock_client_success() -> Generator[MagicMock]:
    """Mock ZowietekClient for successful connection."""
    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        # Use async_get_sys_attr_info instead of async_get_device_info (#49)
        client.async_get_sys_attr_info = AsyncMock(
            return_value={
                "SN": "ZBOX-ABC123",
                "device_name": "ZowieBox-Office",
                "firmware_version": "1.2.3",
            }
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        yield mock_client_class


# =============================================================================
# User Step Tests - Device Picker
# =============================================================================


async def test_user_form_shown_with_discovered_devices(
    hass: HomeAssistant,
    mock_discovery_one_device: AsyncMock,
) -> None:
    """Test that the user form shows device picker when devices are discovered."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    # Note: errors key may not be present when no errors occurred
    assert result.get("errors") in (None, {})


async def test_user_form_shown_no_devices(
    hass: HomeAssistant,
    mock_discovery_no_devices: AsyncMock,
) -> None:
    """Test that the manual form is shown when no devices are discovered."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # When no devices found, skip directly to manual entry
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {}


async def test_user_form_shown_on_discovery_error(
    hass: HomeAssistant,
    mock_discovery_error: AsyncMock,
) -> None:
    """Test that the manual form is shown when discovery fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # When discovery fails, go directly to manual entry
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"


async def test_user_selects_manual_entry(
    hass: HomeAssistant,
    mock_discovery_one_device: AsyncMock,
) -> None:
    """Test user selecting manual entry redirects to manual step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select manual entry option
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"device": "manual"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"


async def test_user_selects_discovered_device(
    hass: HomeAssistant,
    mock_discovery_one_device: AsyncMock,
) -> None:
    """Test user selecting a discovered device redirects to credentials step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select the discovered device
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"device": "ZBOX-ABC123"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"


# =============================================================================
# Manual Entry Flow Tests
# =============================================================================


async def test_successful_manual_config_flow(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_discovery_no_devices: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test successful manual config flow creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # No devices found, goes directly to manual entry
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

    # Submit manual entry form
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ZowieBox-Office"
    assert result["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "admin",
    }
    # Verify unique_id was set correctly on the config entry
    assert result["result"].unique_id == "ZBOX-ABC123"


async def test_manual_config_flow_connection_error(
    hass: HomeAssistant,
    mock_discovery_no_devices: AsyncMock,
) -> None:
    """Test manual config flow handles connection error."""
    from custom_components.zowietek.exceptions import ZowietekConnectionError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(
            side_effect=ZowietekConnectionError("Connection refused")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        # No devices found, goes directly to manual entry
        assert result["step_id"] == "manual"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "manual"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_manual_config_flow_auth_error(
    hass: HomeAssistant,
    mock_discovery_no_devices: AsyncMock,
) -> None:
    """Test manual config flow handles authentication error."""
    from custom_components.zowietek.exceptions import ZowietekAuthError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(
            side_effect=ZowietekAuthError("Invalid credentials")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        # No devices found, goes directly to manual entry
        assert result["step_id"] == "manual"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "wrong_password",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "manual"
        assert result["errors"] == {"base": "invalid_auth"}


async def test_manual_config_flow_timeout_error(
    hass: HomeAssistant,
    mock_discovery_no_devices: AsyncMock,
) -> None:
    """Test manual config flow handles timeout error."""
    from custom_components.zowietek.exceptions import ZowietekTimeoutError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(
            side_effect=ZowietekTimeoutError("Timeout after 10s")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        # No devices found, goes directly to manual entry
        assert result["step_id"] == "manual"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "manual"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_manual_config_flow_unknown_error(
    hass: HomeAssistant,
    mock_discovery_no_devices: AsyncMock,
) -> None:
    """Test manual config flow handles unknown error."""
    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(side_effect=RuntimeError("Unknown"))
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        # No devices found, goes directly to manual entry
        assert result["step_id"] == "manual"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "manual"
        assert result["errors"] == {"base": "unknown"}


async def test_manual_config_flow_duplicate_device(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_discovery_no_devices: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test manual config flow aborts if device already configured."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        data={
            CONF_HOST: "192.168.1.50",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # No devices found, goes directly to manual entry
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_manual_config_flow_host_url_with_scheme(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_discovery_no_devices: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test manual config flow accepts host with http scheme."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # No devices found, goes directly to manual entry
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "http://192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_manual_config_flow_host_hostname(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_discovery_no_devices: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test manual config flow accepts hostname."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # No devices found, goes directly to manual entry
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "zowiebox.local",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_manual_config_flow_device_info_fallback(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_discovery_no_devices: AsyncMock,
) -> None:
    """Test manual config flow falls back to host-based ID when device info unavailable."""
    from custom_components.zowietek.exceptions import ZowietekApiError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        client.async_get_sys_attr_info = AsyncMock(
            side_effect=ZowietekApiError("Invalid parameters", "00003")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        # No devices found, goes directly to manual entry
        assert result["step_id"] == "manual"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "ZowieBox"
        assert result["result"].unique_id == "http://192.168.1.100"


async def test_manual_config_flow_general_api_error(
    hass: HomeAssistant,
    mock_discovery_no_devices: AsyncMock,
) -> None:
    """Test manual config flow handles general ZowietekError."""
    from custom_components.zowietek.exceptions import ZowietekError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(side_effect=ZowietekError("General API error"))
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        # No devices found, goes directly to manual entry
        assert result["step_id"] == "manual"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "manual"
        assert result["errors"] == {"base": "cannot_connect"}


# =============================================================================
# Credentials Flow Tests (for discovered devices)
# =============================================================================


async def test_credentials_flow_success(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_discovery_one_device: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test successful credentials flow for discovered device creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # Select the discovered device
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"device": "ZBOX-ABC123"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"

    # Submit credentials
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ZowieBox-Office"
    assert result["data"][CONF_HOST] == "http://192.168.1.100:80"
    assert result["data"][CONF_USERNAME] == "admin"
    assert result["data"][CONF_PASSWORD] == "admin"
    assert result["result"].unique_id == "ZBOX-ABC123"


async def test_credentials_flow_auth_error(
    hass: HomeAssistant,
    mock_discovery_one_device: AsyncMock,
) -> None:
    """Test credentials flow handles authentication error."""
    from custom_components.zowietek.exceptions import ZowietekAuthError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(
            side_effect=ZowietekAuthError("Invalid credentials")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"device": "ZBOX-ABC123"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "wrong_password",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "credentials"
        assert result["errors"] == {"base": "invalid_auth"}


async def test_credentials_flow_connection_error(
    hass: HomeAssistant,
    mock_discovery_one_device: AsyncMock,
) -> None:
    """Test credentials flow handles connection error."""
    from custom_components.zowietek.exceptions import ZowietekConnectionError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(
            side_effect=ZowietekConnectionError("Connection refused")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"device": "ZBOX-ABC123"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "credentials"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_credentials_flow_duplicate_device(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_discovery_one_device: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test credentials flow aborts if device already configured."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        data={
            CONF_HOST: "192.168.1.50",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"device": "ZBOX-ABC123"},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# =============================================================================
# Reauthentication Flow Tests
# =============================================================================


async def test_reauth_flow_success(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test successful reauthentication flow updates credentials and reloads."""
    from homeassistant.config_entries import SOURCE_REAUTH
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    # Create existing entry that needs reauthentication
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "old_password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        # Start reauth flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": SOURCE_REAUTH,
                "entry_id": existing_entry.entry_id,
            },
            data=existing_entry.data,
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        # Submit new credentials
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "new_password",
            },
        )

        # Should abort with reauth_successful and update entry
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"

        # Verify credentials were updated
        assert existing_entry.data[CONF_PASSWORD] == "new_password"
        # Host should be preserved
        assert existing_entry.data[CONF_HOST] == "192.168.1.100"


async def test_reauth_flow_invalid_credentials(
    hass: HomeAssistant,
) -> None:
    """Test reauthentication flow shows error for invalid credentials."""
    from homeassistant.config_entries import SOURCE_REAUTH
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.exceptions import ZowietekAuthError

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "old_password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(
            side_effect=ZowietekAuthError("Invalid credentials")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": SOURCE_REAUTH,
                "entry_id": existing_entry.entry_id,
            },
            data=existing_entry.data,
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "wrong_password",
            },
        )

        # Should show form with error
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test reauthentication flow shows error for connection failure."""
    from homeassistant.config_entries import SOURCE_REAUTH
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.exceptions import ZowietekConnectionError

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100"
        client.async_test_connection = AsyncMock(
            side_effect=ZowietekConnectionError("Connection refused")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": SOURCE_REAUTH,
                "entry_id": existing_entry.entry_id,
            },
            data=existing_entry.data,
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "password",
            },
        )

        # Should show form with connection error
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_preserves_host(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reauthentication flow preserves original host and does not allow changing it."""
    from homeassistant.config_entries import SOURCE_REAUTH
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "old_password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": SOURCE_REAUTH,
                "entry_id": existing_entry.entry_id,
            },
            data=existing_entry.data,
        )

        # Form should be shown for reauth_confirm step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        # The form data_schema should only have username and password, not host
        schema_keys = list(result["data_schema"].schema.keys())
        schema_key_names = [str(k) for k in schema_keys]
        assert CONF_HOST not in schema_key_names

        # Submit new credentials
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "newuser",
                CONF_PASSWORD: "newpass",
            },
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"

        # Host should be unchanged
        assert existing_entry.data[CONF_HOST] == "192.168.1.100"
        # Username and password should be updated
        assert existing_entry.data[CONF_USERNAME] == "newuser"
        assert existing_entry.data[CONF_PASSWORD] == "newpass"


async def test_reauth_flow_unknown_error(
    hass: HomeAssistant,
) -> None:
    """Test reauthentication flow handles unknown errors."""
    from homeassistant.config_entries import SOURCE_REAUTH
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(side_effect=RuntimeError("Unknown error"))
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": SOURCE_REAUTH,
                "entry_id": existing_entry.entry_id,
            },
            data=existing_entry.data,
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "password",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {"base": "unknown"}


async def test_reauth_flow_general_api_error(
    hass: HomeAssistant,
) -> None:
    """Test reauthentication flow handles general API errors."""
    from homeassistant.config_entries import SOURCE_REAUTH
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.exceptions import ZowietekError

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(side_effect=ZowietekError("API error"))
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": SOURCE_REAUTH,
                "entry_id": existing_entry.entry_id,
            },
            data=existing_entry.data,
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "password",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {"base": "cannot_connect"}


# =============================================================================
# Options Flow Tests
# =============================================================================


async def test_options_flow_init_form_shown(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow shows form on init."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_has_scan_interval_field(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow form has scan_interval field."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_SCAN_INTERVAL

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    # Verify schema includes scan_interval field
    schema_keys = list(result["data_schema"].schema.keys())
    schema_key_names = [str(k) for k in schema_keys]
    assert CONF_SCAN_INTERVAL in schema_key_names


async def test_options_flow_default_scan_interval(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow shows default scan_interval value."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import DEFAULT_SCAN_INTERVAL

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    # The default value should be shown in the form
    # Schema should have default value of DEFAULT_SCAN_INTERVAL
    schema = result["data_schema"]
    # Get the default value from schema
    for key in schema.schema:
        if hasattr(key, "default"):
            default_val = key.default()
            assert default_val == DEFAULT_SCAN_INTERVAL
            break


async def test_options_flow_saves_scan_interval(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow saves scan_interval to entry.options."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_SCAN_INTERVAL

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 60},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 60


async def test_options_flow_preserves_existing_options(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow uses existing option values as defaults."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_SCAN_INTERVAL

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
        options={CONF_SCAN_INTERVAL: 120},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    # The existing value should be suggested
    suggested_values = result.get("data_schema").schema
    # Find the key and check its default
    for key in suggested_values:
        if str(key) == CONF_SCAN_INTERVAL and hasattr(key, "default") and callable(key.default):
            # The default should be the existing option value
            assert key.default() == 120


async def test_options_flow_min_scan_interval(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow accepts minimum scan_interval of 10 seconds."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_SCAN_INTERVAL

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 10},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 10


async def test_options_flow_max_scan_interval(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow accepts maximum scan_interval of 300 seconds."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_SCAN_INTERVAL

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 300},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 300


async def test_options_flow_handler_registered(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that ZowietekConfigFlow has options flow handler registered."""
    from custom_components.zowietek.config_flow import ZowietekConfigFlow

    # Verify async_get_options_flow is defined
    assert hasattr(ZowietekConfigFlow, "async_get_options_flow")
    # Verify the method is callable
    assert callable(getattr(ZowietekConfigFlow, "async_get_options_flow", None))


async def test_options_flow_has_use_go2rtc_field(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow form has use_go2rtc field."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_USE_GO2RTC

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    # Verify schema includes use_go2rtc field
    schema_keys = list(result["data_schema"].schema.keys())
    schema_key_names = [str(k) for k in schema_keys]
    assert CONF_USE_GO2RTC in schema_key_names


async def test_options_flow_default_use_go2rtc(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow shows default use_go2rtc value."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_USE_GO2RTC, DEFAULT_USE_GO2RTC

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    # Check that the use_go2rtc field has the correct default
    schema = result["data_schema"]
    for key in schema.schema:
        if str(key) == CONF_USE_GO2RTC and hasattr(key, "default"):
            default_val = key.default()
            assert default_val == DEFAULT_USE_GO2RTC
            break


async def test_options_flow_saves_use_go2rtc(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow saves use_go2rtc to entry.options."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_SCAN_INTERVAL, CONF_USE_GO2RTC

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 30, CONF_USE_GO2RTC: False},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_USE_GO2RTC] is False


async def test_options_flow_preserves_existing_use_go2rtc(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that options flow uses existing use_go2rtc value as default."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.const import CONF_SCAN_INTERVAL, CONF_USE_GO2RTC

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
        options={CONF_SCAN_INTERVAL: 30, CONF_USE_GO2RTC: False},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    # Find the key and check its default reflects existing value (False)
    for key in result["data_schema"].schema:
        if str(key) == CONF_USE_GO2RTC and hasattr(key, "default") and callable(key.default):
            assert key.default() is False


# =============================================================================
# Reconfigure Flow Tests
# =============================================================================


async def test_reconfigure_flow_shows_form(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that reconfigure flow shows form with current values."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret_password",
        },
    )
    existing_entry.add_to_hass(hass)

    # Start reconfigure flow
    result = await existing_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"


async def test_reconfigure_flow_prefills_host_and_username(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test that reconfigure form has host and username pre-filled."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret_password",
        },
    )
    existing_entry.add_to_hass(hass)

    result = await existing_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.FORM
    # Check suggested values (for reconfigure, values are in description_placeholders
    # or suggested_values)
    schema_keys = list(result["data_schema"].schema.keys())
    schema_key_names = [str(k) for k in schema_keys]
    assert CONF_HOST in schema_key_names
    assert CONF_USERNAME in schema_key_names
    assert CONF_PASSWORD in schema_key_names


async def test_reconfigure_flow_success(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test successful reconfigure updates entry and reloads."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "old_password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.200"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await existing_entry.start_reconfigure_flow(hass)

        assert result["type"] is FlowResultType.FORM

        # Submit new configuration
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.200",
                CONF_USERNAME: "newadmin",
                CONF_PASSWORD: "new_password",
            },
        )

        # Should abort with reconfigure_successful and update entry
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"

        # Verify all values were updated
        assert existing_entry.data[CONF_HOST] == "192.168.1.200"
        assert existing_entry.data[CONF_USERNAME] == "newadmin"
        assert existing_entry.data[CONF_PASSWORD] == "new_password"


async def test_reconfigure_flow_connection_error(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reconfigure flow shows error for connection failure."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.exceptions import ZowietekConnectionError

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(
            side_effect=ZowietekConnectionError("Connection refused")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await existing_entry.start_reconfigure_flow(hass)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.200",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "password",
            },
        )

        # Should show form with connection error
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_flow_auth_error(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reconfigure flow shows error for invalid credentials."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.exceptions import ZowietekAuthError

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(
            side_effect=ZowietekAuthError("Invalid credentials")
        )
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await existing_entry.start_reconfigure_flow(hass)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "wrong_password",
            },
        )

        # Should show form with auth error
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"] == {"base": "invalid_auth"}


async def test_reconfigure_flow_unknown_error(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reconfigure flow handles unknown errors."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(side_effect=RuntimeError("Unknown error"))
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await existing_entry.start_reconfigure_flow(hass)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "password",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"] == {"base": "unknown"}


async def test_reconfigure_flow_general_api_error(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reconfigure flow handles general API errors."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.zowietek.exceptions import ZowietekError

    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ZBOX-ABC123",
        title="ZowieBox-Office",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(side_effect=ZowietekError("API error"))
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        result = await existing_entry.start_reconfigure_flow(hass)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "password",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"] == {"base": "cannot_connect"}


# =============================================================================
# Tests for _derive_name_from_host
# =============================================================================


class TestDeriveNameFromHost:
    """Tests for _derive_name_from_host static method."""

    def test_derive_name_from_host_with_scheme(self) -> None:
        """Test deriving name from host with scheme (http://)."""
        from custom_components.zowietek.config_flow import ZowietekConfigFlow

        result = ZowietekConfigFlow._derive_name_from_host("http://studio-encoder.local")
        assert result == "ZowieBox (studio-encoder)"

    def test_derive_name_from_host_with_port(self) -> None:
        """Test deriving name from host with port number."""
        from custom_components.zowietek.config_flow import ZowietekConfigFlow

        result = ZowietekConfigFlow._derive_name_from_host("studio-encoder.local:8080")
        assert result == "ZowieBox (studio-encoder)"

    def test_derive_name_from_host_with_scheme_and_port(self) -> None:
        """Test deriving name from host with both scheme and port."""
        from custom_components.zowietek.config_flow import ZowietekConfigFlow

        result = ZowietekConfigFlow._derive_name_from_host("http://studio-encoder.local:8080")
        assert result == "ZowieBox (studio-encoder)"

    def test_derive_name_from_ip_address(self) -> None:
        """Test deriving name from IP address returns plain ZowieBox."""
        from custom_components.zowietek.config_flow import ZowietekConfigFlow

        result = ZowietekConfigFlow._derive_name_from_host("192.168.1.100")
        assert result == "ZowieBox"

    def test_derive_name_from_hostname_with_dots(self) -> None:
        """Test deriving name from hostname with subdomains."""
        from custom_components.zowietek.config_flow import ZowietekConfigFlow

        result = ZowietekConfigFlow._derive_name_from_host("encoder.studio.company.local")
        assert result == "ZowieBox (encoder)"

    def test_derive_name_from_hostname_starting_with_digit(self) -> None:
        """Test deriving name from hostname starting with digit."""
        from custom_components.zowietek.config_flow import ZowietekConfigFlow

        # Hostname starting with a digit - should fall through to plain ZowieBox
        result = ZowietekConfigFlow._derive_name_from_host("123device.local")
        assert result == "ZowieBox"


# =============================================================================
# Tests for credentials step edge case
# =============================================================================


class TestCredentialsStepEdgeCases:
    """Tests for edge cases in credentials step."""

    async def test_credentials_step_without_selected_device_redirects_to_manual(
        self,
        hass: HomeAssistant,
        mock_setup_entry: AsyncMock,
    ) -> None:
        """Test credentials step redirects to manual when no device selected."""
        from custom_components.zowietek.config_flow import ZowietekConfigFlow

        # Create a flow and directly call async_step_credentials without setting _selected_device
        flow = ZowietekConfigFlow()
        flow.hass = hass
        flow._selected_device = None  # Ensure no device is selected

        # This should redirect to manual step
        result = await flow.async_step_credentials()

        # Should redirect to manual step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "manual"
