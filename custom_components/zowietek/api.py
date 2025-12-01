"""ZowieBox API client for the Zowietek integration."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import TYPE_CHECKING, cast

import aiohttp

from .const import (
    STATUS_SUCCESS,
)
from .exceptions import (
    ZowietekApiError,
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekTimeoutError,
)

if TYPE_CHECKING:
    from typing import Any

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10

# API Status Codes
STATUS_NOT_LOGGED_IN = "80003"
STATUS_WRONG_PASSWORD = "80005"
STATUS_INVALID_PARAMS = "00003"


class ZowietekClient:
    """Async client for ZowieBox API.

    This client provides methods for communicating with ZowieBox video
    streaming devices. The ZowieBox API uses a JSON-RPC style interface
    where requests include 'group' and 'opt' fields to specify the operation.

    Most read operations do not require authentication. Write operations
    may require authentication depending on device configuration.

    The client can be used as an async context manager for automatic
    session cleanup.

    Example:
        async with ZowietekClient(host, username, password) as client:
            video_info = await client.async_get_video_info()
            system_time = await client.async_get_system_time()
    """

    __slots__ = (
        "_host",
        "_owns_session",
        "_password",
        "_session",
        "_timeout",
        "_username",
    )

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize ZowietekClient.

        Args:
            host: The hostname or IP address of the ZowieBox device.
            username: Username for authentication (used for write operations).
            password: Password for authentication (used for write operations).
            session: Optional aiohttp ClientSession. If not provided, one will
                be created and managed by this client.
            timeout: Request timeout in seconds. Defaults to 10.
        """
        self._host = self._normalize_host(host)
        self._username = username
        self._password = password
        self._timeout = timeout
        self._session = session
        self._owns_session = session is None

    @staticmethod
    def _normalize_host(host: str) -> str:
        """Normalize the host URL.

        Adds http:// scheme if not present and removes trailing slashes.

        Args:
            host: The host string to normalize.

        Returns:
            Normalized host URL with scheme and without trailing slashes.
        """
        host = host.rstrip("/")
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"
        return host

    @property
    def host(self) -> str:
        """Return the normalized host URL."""
        return self._host

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session.

        Returns:
            The aiohttp ClientSession for making requests.
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(
        self,
        endpoint: str,
        data: dict[str, Any],
        requires_auth: bool = False,
    ) -> dict[str, Any]:
        """Make a POST request to the ZowieBox API.

        Args:
            endpoint: The API endpoint path (e.g., "/video?option=getinfo").
            data: JSON data to send in the request body.
            requires_auth: Whether to include authentication credentials.

        Returns:
            The parsed JSON response data.

        Raises:
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
            ZowietekAuthError: If authentication is required or failed.
            ZowietekApiError: If the API returns an error status.
        """
        session = await self._get_session()

        # Add login_check_flag to query string if not present
        if "login_check_flag" not in endpoint:
            separator = "&" if "?" in endpoint else "?"
            endpoint = f"{endpoint}{separator}login_check_flag=1"

        url = f"{self._host}{endpoint}"

        # Include credentials for authenticated requests
        if requires_auth:
            data = {**data, "user": self._username, "psw": self._password}

        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            async with session.post(url, json=data, timeout=timeout) as response:
                return await self._handle_response(response)
        except TimeoutError as err:
            raise ZowietekTimeoutError(
                f"Request to {url} timed out after {self._timeout} seconds"
            ) from err
        except aiohttp.ClientConnectionError as err:
            raise ZowietekConnectionError(f"Unable to connect to {self._host}: {err}") from err

    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any]:
        """Handle the API response and check for errors.

        Args:
            response: The aiohttp response object.

        Returns:
            The parsed JSON response data.

        Raises:
            ZowietekAuthError: If authentication is required or failed.
            ZowietekApiError: If the API returns an error status.
        """
        try:
            data: dict[str, Any] = await response.json()
        except aiohttp.ContentTypeError as err:
            raise ZowietekApiError(f"Invalid JSON response from device: {err}") from err

        status = str(data.get("status", ""))

        if status in (STATUS_NOT_LOGGED_IN, STATUS_WRONG_PASSWORD):
            raise ZowietekAuthError("Authentication required or failed")

        if status == STATUS_INVALID_PARAMS:
            rsp = data.get("rsp", "Unknown error")
            raise ZowietekApiError(
                f"Invalid parameters: {rsp}",
                status_code=STATUS_INVALID_PARAMS,
            )

        if status != STATUS_SUCCESS:
            rsp = data.get("rsp", "Unknown error")
            raise ZowietekApiError(
                f"API returned error status {status}: {rsp}",
                status_code=status,
            )

        return data

    @staticmethod
    def _extract_data(
        response: dict[str, Any],
        key: str,
    ) -> dict[str, Any]:
        """Extract nested data from API response with proper typing.

        Args:
            response: The full API response dictionary.
            key: The key to extract from the response.

        Returns:
            The nested data dict, or the full response if key is not present.
        """
        value = response.get(key)
        if isinstance(value, dict):
            return cast("dict[str, Any]", value)
        return response

    async def async_test_connection(self) -> bool:
        """Test connection to the device by fetching system time.

        This is a lightweight check that doesn't require authentication.

        Returns:
            True if the connection was successful.

        Raises:
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        await self.async_get_system_time()
        return True

    async def async_validate_credentials(self) -> bool:
        """Validate that the provided credentials are correct.

        Attempts an authenticated request to verify credentials.

        Returns:
            True if credentials are valid.

        Raises:
            ZowietekAuthError: If credentials are invalid.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        # Use a setinfo endpoint that requires auth but has no side effects
        # when called with minimal data
        await self._request(
            "/system?option=setinfo",
            {"group": "user", "user": self._username, "psw": self._password},
            requires_auth=False,  # Credentials are in the body for this specific call
        )
        return True

    async def async_get_system_time(self) -> dict[str, Any]:
        """Get system time from the device.

        Returns:
            System time information including year, month, day, hour, minute, second.
        """
        data = await self._request(
            "/system?option=getinfo",
            {"group": "systime", "opt": "get_systime_info"},
        )
        return self._extract_data(data, "data")

    async def async_get_device_info(self) -> dict[str, Any]:
        """Get device information from the device.

        Returns:
            Device information including serial number, name, and firmware version.
        """
        data = await self._request(
            "/system?option=getinfo",
            {"group": "devinfo"},
        )
        return self._extract_data(data, "data")

    async def async_get_video_info(self) -> dict[str, Any]:
        """Get comprehensive video information from the device.

        Returns:
            Video information including encoding settings, input/output config.
        """
        data = await self._request(
            "/video?option=getinfo",
            {"group": "all"},
        )
        return self._extract_data(data, "all")

    async def async_get_input_signal(self) -> dict[str, Any]:
        """Get HDMI input signal information.

        Returns:
            Input signal details including resolution, framerate, signal presence.
        """
        data = await self._request(
            "/video?option=getinfo",
            {"group": "hdmi", "opt": "get_input_info"},
        )
        return self._extract_data(data, "data")

    async def async_get_output_info(self) -> dict[str, Any]:
        """Get HDMI output configuration.

        Returns:
            Output configuration including format, audio switch status.
        """
        data = await self._request(
            "/video?option=getinfo",
            {"group": "hdmi", "opt": "get_output_info"},
        )
        return self._extract_data(data, "data")

    async def async_get_stream_publish_info(self) -> dict[str, Any]:
        """Get stream publishing information.

        Returns:
            List of configured stream publishing destinations.
        """
        data = await self._request(
            "/stream?option=getinfo",
            {"group": "publish"},
        )
        publish_list = data.get("publish")
        if isinstance(publish_list, list):
            return {"publish": publish_list}
        return {"publish": []}

    async def async_get_ndi_config(self) -> dict[str, Any]:
        """Get NDI configuration.

        Returns:
            NDI configuration and status.
        """
        data = await self._request(
            "/ndi?option=getinfo",
            {"group": "ndi", "opt": "get_config"},
        )
        return self._extract_data(data, "data")

    async def async_set_output_format(self, format_str: str) -> None:
        """Set the HDMI output format.

        Args:
            format_str: Output format (e.g., "1080p60", "2160p30").

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the format is invalid.
        """
        await self._request(
            "/video?option=setinfo",
            {
                "group": "hdmi",
                "opt": "set_output_info",
                "data": {"format": format_str},
            },
            requires_auth=True,
        )

    async def async_set_loop_out(self, enabled: bool) -> None:
        """Enable or disable HDMI loop output.

        Args:
            enabled: True to enable loop output, False to disable.

        Raises:
            ZowietekAuthError: If authentication fails.
        """
        await self._request(
            "/video?option=setinfo",
            {
                "group": "hdmi",
                "opt": "set_output_info",
                "data": {"loop_out_switch": 1 if enabled else 0},
            },
            requires_auth=True,
        )

    async def async_reboot(self) -> None:
        """Reboot the device.

        Raises:
            ZowietekAuthError: If authentication fails.
        """
        await self._request(
            "/system?option=setinfo",
            {"group": "syscontrol", "opt": "set_reboot_info"},
            requires_auth=True,
        )

    async def async_set_ndi_enabled(self, enabled: bool) -> None:
        """Enable or disable NDI streaming.

        Args:
            enabled: True to enable NDI, False to disable.

        Raises:
            ZowietekAuthError: If authentication fails.
        """
        await self._request(
            "/ndi?option=setinfo",
            {
                "group": "ndi",
                "opt": "set_config",
                "data": {"ndi_enable": 1 if enabled else 0},
            },
            requires_auth=True,
        )

    async def async_set_stream_enabled(
        self,
        stream_type: str,
        enabled: bool,
    ) -> None:
        """Enable or disable a stream publishing destination.

        Args:
            stream_type: The stream type ('rtmp' or 'srt').
            enabled: True to enable the stream, False to disable.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the stream type is invalid.
        """
        await self._request(
            "/stream?option=setinfo",
            {
                "group": "publish",
                "opt": "set_enable",
                "type": stream_type,
                "enable": 1 if enabled else 0,
            },
            requires_auth=True,
        )

    async def close(self) -> None:
        """Close the client session.

        Only closes the session if it was created by this client.
        Safe to call multiple times.
        """
        if self._session is not None and self._owns_session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> ZowietekClient:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.close()
