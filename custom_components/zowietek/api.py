"""ZowieBox API client for the Zowietek integration."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import TYPE_CHECKING

import aiohttp

from .const import (
    STATUS_INVALID_PARAMS,
    STATUS_NOT_LOGGED_IN,
    STATUS_SUCCESS,
)
from .exceptions import (
    ZowietekApiError,
    ZowietekAuthError,
    ZowietekConnectionError,
    ZowietekTimeoutError,
)

if TYPE_CHECKING:
    from .models import (
        ZowietekAudioInfo,
        ZowietekNetworkInfo,
        ZowietekStreamInfo,
        ZowietekSystemInfo,
        ZowietekVideoInfo,
    )

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


class ZowietekClient:
    """Async client for ZowieBox API.

    This client provides methods for authenticating with and retrieving
    information from ZowieBox video streaming devices.

    The client can be used as an async context manager for automatic
    session cleanup.

    Example:
        async with ZowietekClient(host, username, password) as client:
            await client.async_login()
            info = await client.async_get_system_info()
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
            username: Username for authentication.
            password: Password for authentication.
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
        data: dict[str, str] | None = None,
    ) -> aiohttp.ClientResponse:
        """Make a POST request to the ZowieBox API.

        Args:
            endpoint: The API endpoint path (e.g., "/system?option=getinfo").
            data: JSON data to send in the request body.

        Returns:
            The aiohttp response object.

        Raises:
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        session = await self._get_session()
        url = f"{self._host}{endpoint}"

        if data is None:
            data = {}

        # Always include credentials in the request
        data["user"] = self._username
        data["psw"] = self._password

        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            return await session.post(url, json=data, timeout=timeout)
        except TimeoutError as err:
            raise ZowietekTimeoutError(
                f"Request to {url} timed out after {self._timeout} seconds"
            ) from err
        except aiohttp.ClientConnectionError as err:
            raise ZowietekConnectionError(f"Unable to connect to {self._host}: {err}") from err

    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
    ) -> dict[str, str | int | bool]:
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
            data: dict[str, str | int | bool] = await response.json()
        except aiohttp.ContentTypeError as err:
            raise ZowietekApiError(f"Invalid JSON response from device: {err}") from err

        status = str(data.get("status", ""))

        if status == STATUS_NOT_LOGGED_IN:
            raise ZowietekAuthError("Authentication required or failed")

        if status == STATUS_INVALID_PARAMS:
            raise ZowietekApiError(
                "Invalid parameters in request",
                status_code=STATUS_INVALID_PARAMS,
            )

        if status != STATUS_SUCCESS:
            raise ZowietekApiError(
                f"API returned error status: {status}",
                status_code=status,
            )

        return data

    async def async_login(self) -> bool:
        """Authenticate with the ZowieBox device.

        Returns:
            True if authentication was successful.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/system?option=setinfo&login_check_flag=1",
            {"group": "user"},
        )
        await self._handle_response(response)
        return True

    async def async_get_system_info(self) -> ZowietekSystemInfo:
        """Get system information from the device.

        Returns:
            System information including device name, serial, firmware version.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/system?option=getinfo",
            {"group": "all"},
        )
        data = await self._handle_response(response)
        return data  # type: ignore[return-value]

    async def async_get_video_info(self) -> ZowietekVideoInfo:
        """Get video information from the device.

        Returns:
            Video information including input signal, resolution, framerate.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/video?option=getinfo",
            {"group": "all"},
        )
        data = await self._handle_response(response)
        return data  # type: ignore[return-value]

    async def async_get_audio_info(self) -> ZowietekAudioInfo:
        """Get audio information from the device.

        Returns:
            Audio information including enabled state, codec, volume.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/audio?option=getinfo",
            {"group": "all"},
        )
        data = await self._handle_response(response)
        return data  # type: ignore[return-value]

    async def async_get_stream_info(self) -> ZowietekStreamInfo:
        """Get stream information from the device.

        Returns:
            Stream information including NDI, RTMP, SRT settings.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/stream?option=getinfo",
            {"group": "all"},
        )
        data = await self._handle_response(response)
        return data  # type: ignore[return-value]

    async def async_get_network_info(self) -> ZowietekNetworkInfo:
        """Get network information from the device.

        Returns:
            Network information including IP address, netmask, gateway.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/network?option=getinfo",
            {"group": "all"},
        )
        data = await self._handle_response(response)
        return data  # type: ignore[return-value]

    async def async_set_ndi_enabled(self, enabled: bool) -> None:
        """Enable or disable NDI streaming.

        Args:
            enabled: True to enable NDI, False to disable.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/stream?option=setinfo",
            {"group": "ndi", "ndi_enable": "1" if enabled else "0"},
        )
        await self._handle_response(response)

    async def async_set_rtmp_enabled(self, enabled: bool) -> None:
        """Enable or disable RTMP streaming.

        Args:
            enabled: True to enable RTMP, False to disable.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/stream?option=setinfo",
            {"group": "rtmp", "rtmp_enable": "1" if enabled else "0"},
        )
        await self._handle_response(response)

    async def async_set_srt_enabled(self, enabled: bool) -> None:
        """Enable or disable SRT streaming.

        Args:
            enabled: True to enable SRT, False to disable.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/stream?option=setinfo",
            {"group": "srt", "srt_enable": "1" if enabled else "0"},
        )
        await self._handle_response(response)

    async def async_reboot(self) -> None:
        """Reboot the device.

        Raises:
            ZowietekAuthError: If authentication is required.
            ZowietekApiError: If the API returns an error.
            ZowietekConnectionError: If the connection fails.
            ZowietekTimeoutError: If the request times out.
        """
        response = await self._request(
            "/system?option=setinfo",
            {"group": "reboot", "reboot": "1"},
        )
        await self._handle_response(response)

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
