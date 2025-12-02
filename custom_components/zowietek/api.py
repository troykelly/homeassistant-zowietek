"""ZowieBox API client for the Zowietek integration."""

from __future__ import annotations

import json
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
STATUS_MPP_RESTART = "10000"  # Device is restarting media processing pipeline
STATUS_SUCCESS_ALT = "000000"  # Some endpoints return 6 zeros instead of 5


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
        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
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

        # Status 10000 "mpp restart..." indicates the device is restarting its
        # media processing pipeline. This is a successful operation that occurs
        # when changing encoder codecs or other settings that require a restart.
        # Some endpoints return "000000" (6 zeros) instead of "00000" (5 zeros).
        if status not in (STATUS_SUCCESS, STATUS_SUCCESS_ALT, STATUS_MPP_RESTART):
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

    async def async_get_venc_info(self) -> dict[str, Any]:
        """Get video encoder information from the device.

        Returns:
            Video encoder information with venc array containing all channels.
        """
        data = await self._request(
            "/video?option=getinfo",
            {"group": "venc"},
        )
        # Return the raw response which contains 'venc' array
        return data

    async def async_get_audio_info(self) -> dict[str, Any]:
        """Get audio configuration from the device.

        Returns:
            Audio configuration including input type, codec, sample rate, etc.
        """
        data = await self._request(
            "/audio?option=getinfo",
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

        NDI configuration is under the /video endpoint with group "ndi"
        per the ZowieBox API documentation.

        Returns:
            NDI configuration and status.
        """
        data = await self._request(
            "/video?option=getinfo",
            {"group": "ndi", "opt": "get_ndi_info"},
        )
        return self._extract_data(data, "data")

    async def async_get_sys_attr_info(self) -> dict[str, Any]:
        """Get system attributes including firmware version and serial number.

        This endpoint returns comprehensive device information including:
        - SN: Serial number
        - firmware_version: Firmware version string
        - hardware_version: Hardware version string
        - model: Device model (e.g., "ZowieBox")
        - manufacturer: Manufacturer name
        - device_name: Configured device name
        - ndi_version: NDI library version

        Returns:
            System attributes dictionary.
        """
        data = await self._request(
            "/system?option=getinfo",
            {"group": "sys_attr", "opt": "get_sys_attr_info"},
        )
        return self._extract_data(data, "data")

    async def async_get_dashboard_info(self) -> dict[str, Any]:
        """Get dashboard information including uptime and system stats.

        This endpoint returns:
        - persistent_time: Device uptime as HH:MM:SS string
        - device_strat_time: Device start time as datetime string
        - cpu_temp: CPU temperature in Celsius
        - cpu_payload: CPU usage percentage
        - memory_info: Memory usage statistics

        Returns:
            Dashboard information dictionary.
        """
        data = await self._request(
            "/system?option=getinfo",
            {"group": "get_dashboard_info"},
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

        The device may close the connection before responding, return an empty
        response, or timeout during a reboot. These are all expected behaviors
        and should not raise exceptions.

        Raises:
            ZowietekAuthError: If authentication fails (before reboot starts).
        """
        try:
            await self._request(
                "/system?option=setinfo",
                {
                    "group": "syscontrol",
                    "opt": "set_reboot_info",
                    "data": {"command": "reboot"},
                },
                requires_auth=True,
            )
        except (ZowietekConnectionError, ZowietekTimeoutError, ZowietekApiError):
            # Expected during reboot - device may close connection or not respond
            _LOGGER.debug("Reboot command sent, device may have disconnected")

    async def async_set_ndi_enabled(self, enabled: bool) -> None:
        """Enable or disable NDI streaming.

        NDI configuration is under the /video endpoint with group "ndi"
        per the ZowieBox API documentation.

        Args:
            enabled: True to enable NDI, False to disable.

        Raises:
            ZowietekAuthError: If authentication fails.
        """
        await self._request(
            "/video?option=setinfo",
            {
                "group": "ndi",
                "opt": "set_ndi_info",
                "data": {"switch": 1 if enabled else 0},
            },
            requires_auth=True,
        )

    async def async_set_stream_enabled(
        self,
        stream_type: str,
        enabled: bool,
    ) -> None:
        """Enable or disable a stream publishing destination by type.

        Finds the stream with matching type in the publish list and toggles it.

        Args:
            stream_type: The stream type ('rtmp' or 'srt').
            enabled: True to enable the stream, False to disable.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the stream type is not found.
        """
        # Get current publish list to find index by type
        stream_info = await self.async_get_stream_publish_info()
        publish_list = stream_info.get("publish", [])

        # Find the index for the given stream type
        stream_index: int | None = None
        for entry in publish_list:
            if isinstance(entry, dict) and entry.get("type") == stream_type:
                index = entry.get("index")
                if index is not None:
                    stream_index = int(index)
                    break

        if stream_index is None:
            # Stream type not found in publish list - may not be configured
            raise ZowietekApiError(
                f"Stream type '{stream_type}' not found in publish list",
                "00000",
            )

        await self._request(
            "/stream?option=setinfo",
            {
                "group": "publish",
                "opt": "update_publish_switch",
                "data": {"index": stream_index, "switch": 1 if enabled else 0},
            },
            requires_auth=True,
        )

    async def async_set_encoder_codec(self, codec_id: int) -> None:
        """Set the encoder codec type.

        Args:
            codec_id: The codec index (0=H.264, 1=H.265, 2=MJPEG typically).

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the codec ID is invalid.
        """
        await self._request(
            "/video?option=setinfo",
            {
                "group": "venc",
                "venc": [
                    {
                        "venc_chnid": 0,
                        "codec": {"selected_id": codec_id},
                        "desc": "main",
                    },
                ],
            },
            requires_auth=True,
        )

    async def async_set_ndi_mode(self, mode_id: int) -> None:
        """Set the NDI mode.

        Args:
            mode_id: The NDI mode (1=NDI|HX, 2=NDI|HX2, 3=NDI|HX3).

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the mode ID is invalid.
        """
        await self._request(
            "/video?option=setinfo",
            {
                "group": "ndi",
                "opt": "set_ndi_info",
                "data": {"mode_id": mode_id},
            },
            requires_auth=True,
        )

    async def async_set_audio_volume(self, volume: int) -> None:
        """Set the audio volume.

        Args:
            volume: The volume level (0-100).

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the volume value is invalid or no HDMI signal.

        Note:
            This operation requires an active HDMI input signal. The device
            will return error 10001 "HDMI no signal" if no signal is present.
        """
        await self._request(
            "/audio?option=setinfo",
            {
                "group": "audio",
                "volume": volume,
            },
            requires_auth=True,
        )

    async def async_set_encoder_bitrate(self, bitrate: int) -> None:
        """Set the encoder bitrate.

        Sets the bitrate for the main encoder channel (venc_chnid=0, desc=main).

        Args:
            bitrate: The bitrate in bits per second (e.g., 12000000 for 12 Mbps).

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the bitrate value is invalid.
        """
        await self._request(
            "/video?option=setinfo",
            {
                "group": "venc",
                "venc": [
                    {
                        "venc_chnid": 0,
                        "bitrate": bitrate,
                        "desc": "main",
                    },
                ],
            },
            requires_auth=True,
        )

    async def async_set_ndi_settings(
        self,
        name: str,
        group: str | None = None,
    ) -> None:
        """Set NDI name and group settings.

        Configures the NDI source name and optionally the group.
        The ZowieBox API requires the complete NDI configuration to be sent,
        so this method first retrieves the current config, merges the changes,
        and sends the complete structure back.

        Args:
            name: The NDI source name (visible to NDI receivers).
            group: The NDI group name (optional, for organizing sources).

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the settings are invalid.
        """
        # Get current NDI config (API requires complete structure for updates)
        current_config = await self.async_get_ndi_config()

        # Build complete data structure with user's changes merged in
        data: dict[str, str | int | dict[str, str | int]] = {
            "switch": current_config.get("switch", 0),
            "mode_id": current_config.get("mode_id", 1),
            "machinename": name,
            "groups": group if group is not None else current_config.get("groups", "Public"),
            "multicast": current_config.get(
                "multicast",
                {
                    "ttl": 1,
                    "enable": 0,
                    "netmask": "255.255.0.0",
                    "netprefix": "239.255.0.0",
                },
            ),
        }

        await self._request(
            "/video?option=setinfo",
            {
                "group": "ndi",
                "opt": "set_ndi_info",
                "data": data,
            },
            requires_auth=True,
        )

    async def async_set_rtmp_url(
        self,
        url: str,
        key: str | None = None,
    ) -> None:
        """Set RTMP streaming URL and key.

        Configures the RTMP destination URL and optionally the stream key.

        Args:
            url: The RTMP server URL (e.g., rtmp://live.example.com/live).
            key: The stream key for authentication (optional).

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the URL is invalid.
        """
        # Build the full URL with key if provided
        full_url = f"{url}/{key}" if key else url

        await self._request(
            "/stream?option=setinfo",
            {
                "group": "publish",
                "opt": "update_publish_url",
                "data": {
                    "index": 0,  # RTMP is typically index 0
                    "type": "rtmp",
                    "url": full_url,
                },
            },
            requires_auth=True,
        )

    async def async_set_srt_settings(
        self,
        port: int,
        latency: int | None = None,
        passphrase: str | None = None,
    ) -> None:
        """Set SRT streaming settings.

        Configures SRT (Secure Reliable Transport) settings including
        port, latency, and encryption passphrase.

        Args:
            port: The SRT port number (1-65535).
            latency: The SRT latency in milliseconds (optional).
            passphrase: The SRT encryption passphrase (optional).

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the settings are invalid.
        """
        data: dict[str, str | int] = {
            "index": 1,  # SRT is typically index 1
            "type": "srt",
            "port": port,
        }
        if latency is not None:
            data["latency"] = latency
        if passphrase is not None:
            data["passphrase"] = passphrase

        await self._request(
            "/stream?option=setinfo",
            {
                "group": "publish",
                "opt": "update_srt_info",
                "data": data,
            },
            requires_auth=True,
        )

    # =========================================================================
    # Streamplay/Decoder Methods (for decoder mode playback control)
    # =========================================================================

    async def async_get_streamplay_info(self) -> dict[str, Any]:
        """Get streamplay/decoder configuration and status.

        Returns a list of configured playback sources for decoder mode.

        Returns:
            Dictionary containing 'streamplay' list with configured sources.
            Each source has: index, switch, name, streamtype, url, and status info.
        """
        data = await self._request(
            "/streamplay?option=getinfo",
            {"group": "streamplay", "opt": "streamplay_get_all"},
        )
        # The API returns sources in 'data' key as a list, not under 'streamplay'
        # Build a consistent response format
        data_value = data.get("data")
        if isinstance(data_value, list):
            # Sources are directly in 'data' array
            return {"streamplay": data_value}
        if isinstance(data_value, dict):
            # 'data' is a dict, look for 'streamplay' inside it
            streamplay = data_value.get("streamplay", [])
            return {"streamplay": streamplay if isinstance(streamplay, list) else []}
        # Fallback: check if 'streamplay' exists at top level
        streamplay = data.get("streamplay", [])
        return {"streamplay": streamplay if isinstance(streamplay, list) else []}

    async def async_get_decoder_status(self) -> dict[str, Any]:
        """Get current decoder state.

        Returns information about the decoder's current playback state,
        including whether it's playing and what source is active.

        Returns:
            Dictionary containing decoder_state and active source info.
        """
        data = await self._request(
            "/streamplay?option=getinfo",
            {"group": "streamplay", "opt": "get_decoder_state"},
        )
        return self._extract_data(data, "data")

    async def async_add_decoding_url(
        self,
        name: str,
        url: str,
        streamtype: int = 1,
        switch: bool = True,
    ) -> None:
        """Add a new playback source for decoder mode.

        Args:
            name: Display name for the source.
            url: Stream URL (rtsp://, srt://, rtmp://, http://, etc.).
            streamtype: Stream type (0=local, 1=live). Defaults to 1 (live).
            switch: Whether to enable the source immediately. Defaults to True.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the operation fails.
        """
        await self._request(
            "/streamplay?option=setinfo",
            {
                "group": "streamplay",
                "opt": "streamplay_add",
                "name": name,
                "url": url,
                "streamtype": streamtype,
                "switch": 1 if switch else 0,
            },
            requires_auth=True,
        )

    async def async_modify_decoding_url(
        self,
        index: int,
        name: str,
        url: str,
        streamtype: int = 1,
        switch: bool = True,
    ) -> None:
        """Modify an existing playback source.

        Args:
            index: Index of the source to modify.
            name: New display name for the source.
            url: New stream URL.
            streamtype: Stream type (0=local, 1=live). Defaults to 1 (live).
            switch: Whether the source should be enabled. Defaults to True.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the operation fails.
        """
        await self._request(
            "/streamplay?option=setinfo",
            {
                "group": "streamplay",
                "opt": "streamplay_modify",
                "index": index,
                "name": name,
                "url": url,
                "streamtype": streamtype,
                "switch": 1 if switch else 0,
            },
            requires_auth=True,
        )

    async def async_delete_decoding_url(self, index: int) -> None:
        """Delete a playback source.

        Args:
            index: Index of the source to delete.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the operation fails.
        """
        await self._request(
            "/streamplay?option=setinfo",
            {
                "group": "streamplay",
                "opt": "streamplay_del",
                "index": index,
            },
            requires_auth=True,
        )

    async def async_select_streamplay_source(self, index: int) -> None:
        """Select and activate a streamplay source by index.

        Uses the streamplay_switch operation to enable the specified source.

        Args:
            index: Index of the source to activate.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the operation fails.
        """
        await self._request(
            "/streamplay?option=setinfo",
            {
                "group": "streamplay",
                "opt": "streamplay_switch",
                "data": {"index": index, "switch": 1},
            },
            requires_auth=True,
        )

    async def async_stop_streamplay(self) -> None:
        """Stop current streamplay/decoder playback.

        Finds the currently active source (switch=1) and disables it.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the operation fails.
        """
        # First get all sources to find the active one
        streamplay_info = await self.async_get_streamplay_info()
        sources = streamplay_info.get("streamplay", [])

        # Find the source with switch=1 (active)
        active_index: int | None = None
        for source in sources:
            if isinstance(source, dict) and source.get("switch") == 1:
                active_index = source.get("index")
                break

        if active_index is None:
            # No active source, nothing to stop
            return

        # Disable the active source
        await self._request(
            "/streamplay?option=setinfo",
            {
                "group": "streamplay",
                "opt": "streamplay_switch",
                "data": {"index": active_index, "switch": 0},
            },
            requires_auth=True,
        )

    async def async_enable_ndi_decoding(self, ndi_name: str) -> None:
        """Enable NDI source for decoder playback.

        Args:
            ndi_name: The NDI source name (e.g., "CAMERA1 (Channel 1)").

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the operation fails.
        """
        await self._request(
            "/streamplay?option=setinfo",
            {
                "group": "streamplay",
                "opt": "ndi_enable",
                "ndi_name": ndi_name,
            },
            requires_auth=True,
        )

    async def async_disable_ndi_decoding(self) -> None:
        """Disable NDI decoder playback.

        Raises:
            ZowietekAuthError: If authentication fails.
            ZowietekApiError: If the operation fails.
        """
        await self._request(
            "/streamplay?option=setinfo",
            {
                "group": "streamplay",
                "opt": "ndi_close",
            },
            requires_auth=True,
        )

    async def async_get_ndi_sources(self) -> dict[str, Any]:
        """Get list of discovered NDI sources.

        Returns:
            Dictionary containing 'ndi_sources' list with available sources.
            Each source has: index, name, url.
        """
        data = await self._request(
            "/streamplay?option=getinfo",
            {"group": "streamplay", "opt": "ndi_get_sources"},
        )
        result = self._extract_data(data, "data")
        # Ensure ndi_sources key exists
        if "ndi_sources" not in result:
            result["ndi_sources"] = []
        return result

    async def async_ndi_find(self) -> None:
        """Trigger NDI source discovery.

        Initiates a scan for NDI sources on the network. After calling this,
        use async_get_ndi_sources() to retrieve the discovered sources.
        """
        await self._request(
            "/streamplay?option=setinfo",
            {"group": "streamplay", "opt": "ndi_find"},
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
