"""Config flow for Zowietek integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback

from .api import ZowietekClient
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .exceptions import (
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

# Placeholder for password field in reconfigure flow
PASSWORD_PLACEHOLDER = "**********"


class ZowietekConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zowietek."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: ConfigEntry[Any] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry[Any],
    ) -> ZowietekOptionsFlow:
        """Get the options flow for this handler.

        Args:
            config_entry: The config entry to configure.

        Returns:
            The options flow handler.
        """
        return ZowietekOptionsFlow(config_entry)

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
                # Get unique_id - prefer device serial, fall back to normalized host
                device_sn = device_info.get("devicesn", "")
                device_name = device_info.get("devicename", "")
                normalized_host = device_info.get("normalized_host", host)

                # Use device serial if available, otherwise use normalized host
                unique_id = device_sn if device_sn else normalized_host
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Use device name if available, otherwise derive from host
                if not device_name:
                    device_name = self._derive_name_from_host(host)

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
            Device info dictionary with devicesn, devicename, and normalized_host.
        """
        result: dict[str, Any] = {
            "devicesn": "",
            "devicename": "",
            "softver": "",
            "normalized_host": client.host,
        }

        # Try to get device info from API (not all firmware versions support this)
        try:
            data = await client.async_get_device_info()
            result["devicesn"] = data.get("devicesn", "")
            result["devicename"] = data.get("devicename", "")
            result["softver"] = data.get("softver", "")
        except ZowietekError:
            # Device info endpoint not supported - use host-based identification
            _LOGGER.debug(
                "Device info API not available for %s, using host-based identification",
                client.host,
            )

        return result

    @staticmethod
    def _derive_name_from_host(host: str) -> str:
        """Derive a friendly device name from the host.

        Args:
            host: The host/IP address of the device.

        Returns:
            A friendly device name.
        """
        # Remove scheme if present
        name = host
        if "://" in name:
            name = name.split("://", 1)[1]

        # Remove port if present
        if ":" in name:
            name = name.rsplit(":", 1)[0]

        # If it's an IP address, just use "ZowieBox"
        if name.replace(".", "").isdigit():
            return "ZowieBox"

        # Use hostname part (first segment before dots for subdomains)
        parts = name.split(".")
        if len(parts) > 0:
            hostname = parts[0]
            # Capitalize if it looks like a name
            if hostname and not hostname[0].isdigit():
                return f"ZowieBox ({hostname})"

        return "ZowieBox"

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],
    ) -> ConfigFlowResult:
        """Handle reauthentication.

        This is called when the coordinator raises ConfigEntryAuthFailed,
        indicating that the stored credentials are no longer valid.

        Args:
            entry_data: The current config entry data.

        Returns:
            ConfigFlowResult forwarding to reauth_confirm step.
        """
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle reauthentication confirmation.

        Shows a form for the user to enter new credentials. The host is
        preserved from the original entry and cannot be changed.

        Args:
            user_input: The user input from the form, or None on first call.

        Returns:
            ConfigFlowResult with form on error or abort on success.
        """
        errors: dict[str, str] = {}

        if user_input is not None and self._reauth_entry is not None:
            host = self._reauth_entry.data[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Validate new credentials
            valid = await self._async_validate_reauth(host, username, password, errors)

            if valid:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
        )

    async def _async_validate_reauth(
        self,
        host: str,
        username: str,
        password: str,
        errors: dict[str, str],
    ) -> bool:
        """Validate credentials for reauthentication.

        Args:
            host: The host/IP address of the device.
            username: The new username.
            password: The new password.
            errors: Dictionary to populate with any errors.

        Returns:
            True if credentials are valid, False otherwise.
        """
        async with ZowietekClient(host, username, password) as client:
            try:
                # Test connectivity and validate credentials
                await client.async_test_connection()
                await client.async_validate_credentials()
                return True
            except ZowietekAuthError:
                _LOGGER.debug("Reauthentication failed for %s", host)
                errors["base"] = "invalid_auth"
            except ZowietekConnectionError:
                _LOGGER.debug("Cannot connect to %s during reauth", host)
                errors["base"] = "cannot_connect"
            except ZowietekError as err:
                _LOGGER.debug("API error during reauth to %s: %s", host, err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth to %s", host)
                errors["base"] = "unknown"

        return False

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the device.

        This flow allows users to update host, username, and password
        from the device's integration page without removing and re-adding.

        Args:
            user_input: The user input from the form, or None on first call.

        Returns:
            ConfigFlowResult with form on error or abort on success.
        """
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # Validate new configuration
            valid = await self._async_validate_reconfigure(host, username, password, errors)

            if valid:
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        # Build schema with current values pre-filled (except password)
        current_host = reconfigure_entry.data.get(CONF_HOST, "")
        current_username = reconfigure_entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Required(CONF_USERNAME, default=current_username): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
        )

    async def _async_validate_reconfigure(
        self,
        host: str,
        username: str,
        password: str,
        errors: dict[str, str],
    ) -> bool:
        """Validate configuration for reconfigure flow.

        Args:
            host: The host/IP address of the device.
            username: The new username.
            password: The new password.
            errors: Dictionary to populate with any errors.

        Returns:
            True if configuration is valid, False otherwise.
        """
        async with ZowietekClient(host, username, password) as client:
            try:
                # Test connectivity and validate credentials
                await client.async_test_connection()
                await client.async_validate_credentials()
                return True
            except ZowietekAuthError:
                _LOGGER.debug("Reconfigure authentication failed for %s", host)
                errors["base"] = "invalid_auth"
            except ZowietekConnectionError:
                _LOGGER.debug("Cannot connect to %s during reconfigure", host)
                errors["base"] = "cannot_connect"
            except ZowietekError as err:
                _LOGGER.debug("API error during reconfigure to %s: %s", host, err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reconfigure to %s", host)
                errors["base"] = "unknown"

        return False


class ZowietekOptionsFlow(OptionsFlow):
    """Handle Zowietek options flow.

    This flow allows users to configure options like polling interval
    after the integration has been set up.
    """

    def __init__(self, config_entry: ConfigEntry[Any]) -> None:
        """Initialize the options flow.

        Args:
            config_entry: The config entry being configured.
        """
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage the options.

        Args:
            user_input: User input from the form, or None on first call.

        Returns:
            ConfigFlowResult with form or create entry.
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current value or default
        current_scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_scan_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
