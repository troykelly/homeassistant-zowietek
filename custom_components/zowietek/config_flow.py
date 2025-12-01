"""Config flow for Zowietek integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

from .api import ZowietekClient
from .const import DEFAULT_PASSWORD, DEFAULT_USERNAME, DOMAIN
from .exceptions import (
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekError,
)

if TYPE_CHECKING:
    from typing import Any

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)


class ZowietekConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zowietek."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step.

        This step collects host, username, and password from the user,
        validates the connection and credentials, and creates the config entry.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Validate connection and credentials
            device_info = await self._async_validate_input(host, username, password, errors)

            if not errors:
                # Get unique_id from device serial number
                device_sn = device_info.get("devicesn", "")
                device_name = device_info.get("devicename", "ZowieBox")

                if device_sn:
                    await self.async_set_unique_id(device_sn)
                    self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=device_name,
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _async_validate_input(
        self,
        host: str,
        username: str,
        password: str,
        errors: dict[str, str],
    ) -> dict[str, Any]:
        """Validate the user input and return device info.

        Args:
            host: The host/IP address of the device.
            username: The username for authentication.
            password: The password for authentication.
            errors: Dictionary to populate with any errors.

        Returns:
            Device information dict if successful, empty dict otherwise.
        """
        device_info: dict[str, Any] = {}

        async with ZowietekClient(host, username, password) as client:
            try:
                # First test basic connectivity
                await client.async_test_connection()

                # Then validate credentials
                await client.async_validate_credentials()

                # Get device info for unique_id and title
                device_info = await self._async_get_device_info(client)

            except ZowietekAuthError:
                _LOGGER.debug("Authentication failed for %s", host)
                errors["base"] = "invalid_auth"
            except ZowietekConnectionError:
                _LOGGER.debug("Cannot connect to %s", host)
                errors["base"] = "cannot_connect"
            except ZowietekError as err:
                _LOGGER.debug("API error connecting to %s: %s", host, err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error connecting to %s", host)
                errors["base"] = "unknown"

        return device_info

    async def _async_get_device_info(
        self,
        client: ZowietekClient,
    ) -> dict[str, Any]:
        """Get device information for config entry.

        Args:
            client: The ZowietekClient instance.

        Returns:
            Device info dictionary with devicesn and devicename.
        """
        data = await client.async_get_device_info()
        return {
            "devicesn": data.get("devicesn", ""),
            "devicename": data.get("devicename", "ZowieBox"),
            "softver": data.get("softver", ""),
        }
