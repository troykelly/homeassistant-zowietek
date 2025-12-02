"""ZowieBox device discovery via UDP multicast.

ZowieBox devices use a proprietary UDP multicast discovery protocol:
- Multicast Address: 224.170.1.242
- Port: 21007
- Protocol: JSON over UDP (IPv4 only)

Message Types:
- check_devices_request: Discovery request
- check_devices_result: Discovery response with device info
- keepalive: Periodic heartbeat (ignored)
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# Discovery protocol constants
MULTICAST_GROUP = "224.170.1.242"
DISCOVERY_PORT = 21007

# Default timeout for discovery (seconds)
DEFAULT_DISCOVERY_TIMEOUT = 3.0

# Discovery request identifier
DISCOVERY_REQUEST_SN = "ha-zowietek"


@dataclass
class DiscoveredDevice:
    """Represents a discovered ZowieBox device.

    Attributes:
        ip: Device IP address.
        web_port: HTTP API port (usually 80).
        device_sn: Device serial number (unique identifier).
        device_name: User-configured device name.
        product_id: Product type identifier.
        workmode_id: Current operating mode.
    """

    ip: str
    web_port: int
    device_sn: str
    device_name: str
    product_id: int
    workmode_id: int

    @classmethod
    def from_dict(cls, data: dict[str, str | int]) -> DiscoveredDevice:
        """Create a DiscoveredDevice from a dictionary.

        Args:
            data: Dictionary containing device data from discovery response.

        Returns:
            A DiscoveredDevice instance.
        """
        return cls(
            ip=str(data.get("ip", "")),
            web_port=int(data.get("web_port", 80)),
            device_sn=str(data.get("device_sn", "")),
            device_name=str(data.get("device_name", "")),
            product_id=int(data.get("product_id", 0)),
            workmode_id=int(data.get("workmode_id", 0)),
        )

    @property
    def host(self) -> str:
        """Return the HTTP host URL for this device.

        Returns:
            URL string in format http://ip:port
        """
        return f"http://{self.ip}:{self.web_port}"


class ZowietekDiscovery:
    """Discover ZowieBox devices on the local network via UDP multicast.

    This class implements the ZowieBox proprietary discovery protocol
    which uses JSON messages over UDP multicast on 224.170.1.242:21007.

    Example:
        discovery = ZowietekDiscovery(timeout=5.0)
        devices = await discovery.async_discover()
        for device in devices:
            print(f"Found: {device.device_name} at {device.ip}")
    """

    def __init__(self, timeout: float = DEFAULT_DISCOVERY_TIMEOUT) -> None:
        """Initialize the discovery instance.

        Args:
            timeout: How long to wait for responses (seconds).
        """
        self.timeout = timeout

    def _build_discovery_request(self) -> bytes:
        """Build the discovery request message.

        Returns:
            JSON-encoded discovery request as bytes.
        """
        request = {
            "opt": "check_devices_request",
            "master_device_sn": DISCOVERY_REQUEST_SN,
        }
        return json.dumps(request).encode("utf-8")

    def _parse_response(self, data: bytes) -> DiscoveredDevice | None:
        """Parse a discovery response message.

        Args:
            data: Raw bytes received from the socket.

        Returns:
            DiscoveredDevice if valid response, None otherwise.
        """
        try:
            message = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.debug("Invalid discovery response: not valid JSON")
            return None

        # Only process check_devices_result messages
        opt = message.get("opt")
        if opt != "check_devices_result":
            if opt == "keepalive":
                _LOGGER.debug("Ignoring keepalive from device")
            else:
                _LOGGER.debug("Ignoring message with opt=%s", opt)
            return None

        # Extract device data
        device_data = message.get("data")
        if not isinstance(device_data, dict):
            _LOGGER.debug("Discovery response missing data field")
            return None

        try:
            return DiscoveredDevice.from_dict(device_data)
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.debug("Failed to parse device data: %s", err)
            return None

    async def async_discover(self) -> list[DiscoveredDevice]:
        """Discover ZowieBox devices on the network.

        Sends a discovery request to the multicast group and collects
        responses until the timeout expires.

        Returns:
            List of discovered devices (deduplicated by serial number).

        Raises:
            OSError: If there's a network error (socket creation, etc).
        """
        devices: dict[str, DiscoveredDevice] = {}
        sock: socket.socket | None = None

        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.setblocking(False)

            # Join multicast group to receive responses
            mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            # Bind to receive responses on the discovery port
            sock.bind(("", DISCOVERY_PORT))

            # Send discovery request
            request = self._build_discovery_request()
            sock.sendto(request, (MULTICAST_GROUP, DISCOVERY_PORT))
            _LOGGER.debug("Sent discovery request to %s:%s", MULTICAST_GROUP, DISCOVERY_PORT)

            # Collect responses until timeout
            loop = asyncio.get_event_loop()
            end_time = loop.time() + self.timeout

            while loop.time() < end_time:
                remaining = end_time - loop.time()
                if remaining <= 0:
                    break

                try:
                    # Use asyncio to wait for data with timeout
                    data, addr = await asyncio.wait_for(
                        loop.sock_recvfrom(sock, 4096),
                        timeout=min(remaining, 0.5),
                    )
                    _LOGGER.debug("Received response from %s", addr)

                    device = self._parse_response(data)
                    if device and device.device_sn and device.device_sn not in devices:
                        # Deduplicate by serial number
                        devices[device.device_sn] = device
                        _LOGGER.debug(
                            "Discovered device: %s (%s)",
                            device.device_name,
                            device.ip,
                        )
                except TimeoutError:
                    # No response within the interval, continue waiting
                    continue

        finally:
            if sock is not None:
                sock.close()

        _LOGGER.info("Discovery complete: found %d device(s)", len(devices))
        return list(devices.values())


async def async_discover_devices(
    timeout: float = DEFAULT_DISCOVERY_TIMEOUT,
) -> list[DiscoveredDevice]:
    """Convenience function to discover ZowieBox devices.

    Args:
        timeout: How long to wait for responses (seconds).

    Returns:
        List of discovered devices.
    """
    discovery = ZowietekDiscovery(timeout=timeout)
    return await discovery.async_discover()
