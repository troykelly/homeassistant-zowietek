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

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


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


async def test_user_form_shown(hass: HomeAssistant) -> None:
    """Test that the user form is shown on initial step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_config_flow(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test successful config flow creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM

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


async def test_config_flow_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow handles connection error."""
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
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_auth_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow handles authentication error."""
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
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "wrong_password",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_config_flow_timeout_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow handles timeout error."""
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

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_unknown_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow handles unknown error."""
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

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_config_flow_duplicate_device(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test config flow aborts if device already configured."""
    # First, create an existing entry with the same unique_id
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

    # Now try to configure the same device
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

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


async def test_config_flow_form_redisplay_on_error(
    hass: HomeAssistant,
) -> None:
    """Test that form is redisplayed with user's input after error."""
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
            {
                CONF_HOST: "my-zowiebox.local",
                CONF_USERNAME: "myuser",
                CONF_PASSWORD: "mypass",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}
        # Form should still have the schema for re-entry


async def test_config_flow_host_url_with_scheme(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test config flow accepts host with http scheme."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "http://192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_config_flow_host_hostname(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_client_success: MagicMock,
) -> None:
    """Test config flow accepts hostname."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "zowiebox.local",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_config_flow_device_info_fallback(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow falls back to host-based ID when device info unavailable."""
    from custom_components.zowietek.exceptions import ZowietekApiError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        # Sys attr endpoint not supported - should fall back gracefully (#49)
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

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        # Should succeed with host-based unique_id
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "ZowieBox"
        assert result["result"].unique_id == "http://192.168.1.100"


async def test_config_flow_sys_attr_fallback_with_hostname(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow derives name from hostname when sys attr unavailable."""
    from custom_components.zowietek.exceptions import ZowietekApiError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://zow001.example.com"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        # Sys attr endpoint not supported - should fall back gracefully (#49)
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

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "zow001.example.com",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        # Should succeed with hostname-derived name
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "ZowieBox (zow001)"
        assert result["result"].unique_id == "http://zow001.example.com"


async def test_config_flow_general_api_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow handles general ZowietekError."""
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

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_host_with_scheme_and_port(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow with host that has scheme and port."""
    from custom_components.zowietek.exceptions import ZowietekApiError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://192.168.1.100:8080"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        # Sys attr unavailable - tests _derive_name_from_host (#49)
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

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "http://192.168.1.100:8080",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        # Port is stripped, IP returns "ZowieBox"
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "ZowieBox"


async def test_config_flow_host_with_port_and_subdomain(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow with host with port and subdomain."""
    from custom_components.zowietek.exceptions import ZowietekApiError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.host = "http://zow001.local:8080"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        # Sys attr unavailable - tests _derive_name_from_host (#49)
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

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "http://zow001.local:8080",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        # Port stripped, hostname derived
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "ZowieBox (zow001)"


async def test_config_flow_empty_hostname_fallback(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow with edge case where hostname is empty after parsing."""
    from custom_components.zowietek.exceptions import ZowietekApiError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        # Edge case: just dots after scheme/port stripping
        client.host = "http://....:8080"
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        # Sys attr unavailable - tests _derive_name_from_host fallback (#49)
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

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "....:8080",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "admin",
            },
        )

        # Should fall back to "ZowieBox"
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "ZowieBox"


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
