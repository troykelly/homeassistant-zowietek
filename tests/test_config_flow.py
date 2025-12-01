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
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        client.async_get_device_info = AsyncMock(
            return_value={
                "devicesn": "ZBOX-ABC123",
                "devicename": "ZowieBox-Office",
                "softver": "1.2.3",
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


async def test_config_flow_api_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow handles API error during device info fetch."""
    from custom_components.zowietek.exceptions import ZowietekApiError

    with patch(
        "custom_components.zowietek.config_flow.ZowietekClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_validate_credentials = AsyncMock(return_value=True)
        client.async_get_device_info = AsyncMock(
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

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}
