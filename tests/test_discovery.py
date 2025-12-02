"""Tests for Zowietek device discovery module."""

from __future__ import annotations

import asyncio
import json
import socket
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.zowietek.discovery import (
    DISCOVERY_PORT,
    MULTICAST_GROUP,
    DiscoveredDevice,
    ZowietekDiscovery,
    async_discover_devices,
)

if TYPE_CHECKING:
    from collections.abc import Generator


# Test constants matching the protocol specification
EXPECTED_MULTICAST_GROUP = "224.170.1.242"
EXPECTED_DISCOVERY_PORT = 21007


class TestDiscoveryConstants:
    """Test discovery protocol constants."""

    def test_multicast_group_address(self) -> None:
        """Test multicast group address is correct."""
        assert MULTICAST_GROUP == EXPECTED_MULTICAST_GROUP

    def test_discovery_port(self) -> None:
        """Test discovery port is correct."""
        assert DISCOVERY_PORT == EXPECTED_DISCOVERY_PORT


class TestDiscoveredDevice:
    """Test DiscoveredDevice data class."""

    def test_create_discovered_device(self) -> None:
        """Test creating a DiscoveredDevice instance."""
        device = DiscoveredDevice(
            ip="10.61.22.241",
            web_port=80,
            device_sn="27117",
            device_name="ZowieBox-27117",
            product_id=2,
            workmode_id=1,
        )
        assert device.ip == "10.61.22.241"
        assert device.web_port == 80
        assert device.device_sn == "27117"
        assert device.device_name == "ZowieBox-27117"
        assert device.product_id == 2
        assert device.workmode_id == 1

    def test_discovered_device_from_dict(self) -> None:
        """Test creating DiscoveredDevice from API response dict."""
        data = {
            "ip": "10.61.22.243",
            "web_port": 80,
            "device_sn": "25859",
            "device_name": "ZowieBox-25859",
            "product_id": 2,
            "workmode_id": 1,
        }
        device = DiscoveredDevice.from_dict(data)
        assert device.ip == "10.61.22.243"
        assert device.web_port == 80
        assert device.device_sn == "25859"
        assert device.device_name == "ZowieBox-25859"

    def test_discovered_device_from_dict_missing_optional_fields(self) -> None:
        """Test creating DiscoveredDevice with missing optional fields."""
        data = {
            "ip": "192.168.1.100",
            "web_port": 80,
            "device_sn": "12345",
            "device_name": "ZowieBox-12345",
        }
        device = DiscoveredDevice.from_dict(data)
        assert device.ip == "192.168.1.100"
        assert device.product_id == 0  # default
        assert device.workmode_id == 0  # default

    def test_discovered_device_host_property(self) -> None:
        """Test the host property returns correct URL format."""
        device = DiscoveredDevice(
            ip="192.168.1.100",
            web_port=80,
            device_sn="12345",
            device_name="Test",
            product_id=2,
            workmode_id=1,
        )
        assert device.host == "http://192.168.1.100:80"

    def test_discovered_device_host_property_non_standard_port(self) -> None:
        """Test host property with non-standard port."""
        device = DiscoveredDevice(
            ip="192.168.1.100",
            web_port=8080,
            device_sn="12345",
            device_name="Test",
            product_id=2,
            workmode_id=1,
        )
        assert device.host == "http://192.168.1.100:8080"


class TestZowietekDiscovery:
    """Test ZowietekDiscovery class."""

    def test_create_discovery_instance(self) -> None:
        """Test creating a ZowietekDiscovery instance."""
        discovery = ZowietekDiscovery()
        assert discovery is not None
        assert discovery.timeout == 3.0  # default timeout

    def test_create_discovery_with_custom_timeout(self) -> None:
        """Test creating ZowietekDiscovery with custom timeout."""
        discovery = ZowietekDiscovery(timeout=5.0)
        assert discovery.timeout == 5.0

    def test_build_discovery_request(self) -> None:
        """Test building the discovery request message."""
        discovery = ZowietekDiscovery()
        request = discovery._build_discovery_request()

        # Parse the request as JSON
        data = json.loads(request.decode("utf-8"))

        assert data["opt"] == "check_devices_request"
        assert "master_device_sn" in data

    def test_parse_discovery_response_valid(self) -> None:
        """Test parsing a valid discovery response."""
        discovery = ZowietekDiscovery()
        response = json.dumps(
            {
                "opt": "check_devices_result",
                "master_device_sn": "00000",
                "data": {
                    "ip": "10.61.22.241",
                    "web_port": 80,
                    "device_sn": "27117",
                    "device_name": "ZowieBox-27117",
                    "product_id": 2,
                    "workmode_id": 1,
                },
            }
        ).encode("utf-8")

        device = discovery._parse_response(response)
        assert device is not None
        assert device.ip == "10.61.22.241"
        assert device.device_name == "ZowieBox-27117"

    def test_parse_discovery_response_keepalive_ignored(self) -> None:
        """Test that keepalive messages are ignored."""
        discovery = ZowietekDiscovery()
        response = json.dumps(
            {
                "opt": "keepalive",
                "master_device_sn": "25859",
            }
        ).encode("utf-8")

        device = discovery._parse_response(response)
        assert device is None

    def test_parse_discovery_response_invalid_json(self) -> None:
        """Test parsing invalid JSON returns None."""
        discovery = ZowietekDiscovery()
        response = b"not valid json"

        device = discovery._parse_response(response)
        assert device is None

    def test_parse_discovery_response_missing_data(self) -> None:
        """Test parsing response without data field returns None."""
        discovery = ZowietekDiscovery()
        response = json.dumps(
            {
                "opt": "check_devices_result",
                "master_device_sn": "00000",
            }
        ).encode("utf-8")

        device = discovery._parse_response(response)
        assert device is None


class TestAsyncDiscovery:
    """Test async discovery functionality."""

    @pytest.fixture
    def mock_socket(self) -> Generator[MagicMock]:
        """Create a mock socket for testing."""
        with patch("socket.socket") as mock_sock_class:
            mock_sock = MagicMock()
            mock_sock_class.return_value = mock_sock
            # Mark socket as non-blocking (required for asyncio)
            mock_sock.setblocking = MagicMock()
            yield mock_sock

    def _create_async_recvfrom_mock(
        self, responses: list[tuple[bytes, tuple[str, int]] | type[Exception]]
    ) -> AsyncMock:
        """Create an async mock for loop.sock_recvfrom.

        Args:
            responses: List of (data, addr) tuples or exception types.

        Returns:
            AsyncMock that returns responses in order then raises TimeoutError.
        """
        call_count = 0

        async def mock_recvfrom(sock: MagicMock, bufsize: int) -> tuple[bytes, tuple[str, int]]:
            nonlocal call_count
            if call_count < len(responses):
                response = responses[call_count]
                call_count += 1
                if isinstance(response, type) and issubclass(response, Exception):
                    raise response()
                return response
            # After all responses, keep raising TimeoutError
            raise TimeoutError()

        return AsyncMock(side_effect=mock_recvfrom)

    @pytest.mark.asyncio
    async def test_discover_devices_returns_list(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test that discover returns a list of devices."""
        response_data = json.dumps(
            {
                "opt": "check_devices_result",
                "master_device_sn": "00000",
                "data": {
                    "ip": "10.61.22.241",
                    "web_port": 80,
                    "device_sn": "27117",
                    "device_name": "ZowieBox-27117",
                    "product_id": 2,
                    "workmode_id": 1,
                },
            }
        ).encode("utf-8")

        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            self._create_async_recvfrom_mock(
                [
                    (response_data, ("10.61.22.241", 21007)),
                ]
            ),
        ):
            discovery = ZowietekDiscovery(timeout=0.5)
            devices = await discovery.async_discover()

        assert isinstance(devices, list)
        assert len(devices) == 1
        assert devices[0].ip == "10.61.22.241"

    @pytest.mark.asyncio
    async def test_discover_devices_multiple_responses(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test discovery with multiple device responses."""
        response1 = json.dumps(
            {
                "opt": "check_devices_result",
                "master_device_sn": "00000",
                "data": {
                    "ip": "10.61.22.241",
                    "web_port": 80,
                    "device_sn": "27117",
                    "device_name": "ZowieBox-27117",
                    "product_id": 2,
                    "workmode_id": 1,
                },
            }
        ).encode("utf-8")

        response2 = json.dumps(
            {
                "opt": "check_devices_result",
                "master_device_sn": "00000",
                "data": {
                    "ip": "10.61.22.243",
                    "web_port": 80,
                    "device_sn": "25859",
                    "device_name": "ZowieBox-25859",
                    "product_id": 2,
                    "workmode_id": 1,
                },
            }
        ).encode("utf-8")

        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            self._create_async_recvfrom_mock(
                [
                    (response1, ("10.61.22.241", 21007)),
                    (response2, ("10.61.22.243", 21007)),
                ]
            ),
        ):
            discovery = ZowietekDiscovery(timeout=0.5)
            devices = await discovery.async_discover()

        assert len(devices) == 2
        device_ips = {d.ip for d in devices}
        assert "10.61.22.241" in device_ips
        assert "10.61.22.243" in device_ips

    @pytest.mark.asyncio
    async def test_discover_devices_no_responses(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test discovery with no device responses."""
        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            self._create_async_recvfrom_mock([]),
        ):
            discovery = ZowietekDiscovery(timeout=0.2)
            devices = await discovery.async_discover()

        assert isinstance(devices, list)
        assert len(devices) == 0

    @pytest.mark.asyncio
    async def test_discover_devices_filters_duplicates(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test that duplicate responses are filtered."""
        response = json.dumps(
            {
                "opt": "check_devices_result",
                "master_device_sn": "00000",
                "data": {
                    "ip": "10.61.22.241",
                    "web_port": 80,
                    "device_sn": "27117",
                    "device_name": "ZowieBox-27117",
                    "product_id": 2,
                    "workmode_id": 1,
                },
            }
        ).encode("utf-8")

        # Same device responds twice
        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            self._create_async_recvfrom_mock(
                [
                    (response, ("10.61.22.241", 21007)),
                    (response, ("10.61.22.241", 21007)),
                ]
            ),
        ):
            discovery = ZowietekDiscovery(timeout=0.5)
            devices = await discovery.async_discover()

        assert len(devices) == 1

    @pytest.mark.asyncio
    async def test_discover_devices_ignores_keepalive(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test that keepalive messages don't create device entries."""
        keepalive = json.dumps(
            {
                "opt": "keepalive",
                "master_device_sn": "25859",
            }
        ).encode("utf-8")

        discovery_response = json.dumps(
            {
                "opt": "check_devices_result",
                "master_device_sn": "00000",
                "data": {
                    "ip": "10.61.22.241",
                    "web_port": 80,
                    "device_sn": "27117",
                    "device_name": "ZowieBox-27117",
                    "product_id": 2,
                    "workmode_id": 1,
                },
            }
        ).encode("utf-8")

        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            self._create_async_recvfrom_mock(
                [
                    (keepalive, ("10.61.22.243", 21007)),
                    (discovery_response, ("10.61.22.241", 21007)),
                ]
            ),
        ):
            discovery = ZowietekDiscovery(timeout=0.5)
            devices = await discovery.async_discover()

        assert len(devices) == 1
        assert devices[0].device_sn == "27117"

    @pytest.mark.asyncio
    async def test_discover_socket_configuration(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test that socket is configured correctly for multicast."""
        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            self._create_async_recvfrom_mock([]),
        ):
            discovery = ZowietekDiscovery(timeout=0.2)
            await discovery.async_discover()

        # Verify socket was configured for multicast
        mock_socket.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_socket.setsockopt.assert_any_call(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    @pytest.mark.asyncio
    async def test_discover_sends_request_to_multicast(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test that discovery request is sent to multicast address."""
        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            self._create_async_recvfrom_mock([]),
        ):
            discovery = ZowietekDiscovery(timeout=0.2)
            await discovery.async_discover()

        # Verify sendto was called with multicast address and port
        mock_socket.sendto.assert_called_once()
        call_args = mock_socket.sendto.call_args
        assert call_args[0][1] == (EXPECTED_MULTICAST_GROUP, EXPECTED_DISCOVERY_PORT)

    @pytest.mark.asyncio
    async def test_discover_closes_socket(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test that socket is closed after discovery."""
        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            self._create_async_recvfrom_mock([]),
        ):
            discovery = ZowietekDiscovery(timeout=0.2)
            await discovery.async_discover()

        mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_closes_socket_on_error(
        self,
        mock_socket: MagicMock,
    ) -> None:
        """Test that socket is closed even if an error occurs."""

        async def raise_error(sock: MagicMock, bufsize: int) -> tuple[bytes, tuple[str, int]]:
            raise OSError("Network error")

        with patch.object(
            asyncio.get_event_loop(),
            "sock_recvfrom",
            AsyncMock(side_effect=raise_error),
        ):
            discovery = ZowietekDiscovery(timeout=0.2)

            with pytest.raises(OSError):
                await discovery.async_discover()

        mock_socket.close.assert_called_once()


class TestAsyncDiscoverDevicesFunction:
    """Test the async_discover_devices convenience function."""

    @pytest.mark.asyncio
    async def test_async_discover_devices_returns_list(self) -> None:
        """Test async_discover_devices returns list."""
        with patch.object(
            ZowietekDiscovery, "async_discover", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = [
                DiscoveredDevice(
                    ip="10.61.22.241",
                    web_port=80,
                    device_sn="27117",
                    device_name="ZowieBox-27117",
                    product_id=2,
                    workmode_id=1,
                )
            ]

            devices = await async_discover_devices()

            assert len(devices) == 1
            assert devices[0].ip == "10.61.22.241"

    @pytest.mark.asyncio
    async def test_async_discover_devices_with_timeout(self) -> None:
        """Test async_discover_devices passes timeout."""
        with patch("custom_components.zowietek.discovery.ZowietekDiscovery") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.async_discover = AsyncMock(return_value=[])
            mock_cls.return_value = mock_instance

            await async_discover_devices(timeout=5.0)

            mock_cls.assert_called_once_with(timeout=5.0)


class TestParseResponseEdgeCases:
    """Test edge cases in _parse_response."""

    def test_parse_response_ignores_unknown_opt(self) -> None:
        """Test that _parse_response ignores messages with unknown opt value."""
        discovery = ZowietekDiscovery()

        # Message with unknown opt (not check_devices_result or keepalive)
        message = json.dumps({"opt": "some_other_action", "data": {}}).encode()
        result = discovery._parse_response(message)

        assert result is None

    def test_parse_response_handles_invalid_device_data(self) -> None:
        """Test that _parse_response handles invalid device data that causes TypeError."""
        discovery = ZowietekDiscovery()

        # Message with data that will cause int() conversion to fail
        # web_port = "invalid" will raise ValueError when int() is called
        message = json.dumps(
            {
                "opt": "check_devices_result",
                "data": {
                    "ip": "192.168.1.100",
                    "web_port": "not_a_number",  # This will raise ValueError in int()
                    "device_sn": "ABC123",
                    "device_name": "Test",
                    "product_id": 2,
                    "workmode_id": 1,
                },
            }
        ).encode()

        result = discovery._parse_response(message)

        # Should return None because parsing failed
        assert result is None

    def test_parse_response_handles_non_dict_data_in_response(self) -> None:
        """Test that _parse_response handles when data field is not a dict."""
        discovery = ZowietekDiscovery()

        # Message with data as a list instead of dict
        message = json.dumps({"opt": "check_devices_result", "data": ["not", "a", "dict"]}).encode()

        result = discovery._parse_response(message)

        # Should return None because data is not a dict
        assert result is None


class TestAsyncDiscoverTimeoutBehavior:
    """Test timeout behavior in async_discover."""

    @pytest.mark.asyncio
    async def test_discover_exits_when_remaining_time_zero(self) -> None:
        """Test that discovery loop exits when remaining time is zero or negative."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            # Simulate a scenario where loop.time() advances quickly
            call_count = 0

            async def slow_recvfrom(sock: MagicMock, bufsize: int) -> tuple[bytes, tuple[str, int]]:
                nonlocal call_count
                call_count += 1
                # After first call, raise timeout to let the loop check time
                await asyncio.sleep(0.01)
                raise TimeoutError("timeout")

            with patch.object(
                asyncio.get_event_loop(),
                "sock_recvfrom",
                slow_recvfrom,
            ):
                # Very short timeout
                discovery = ZowietekDiscovery(timeout=0.05)
                devices = await discovery.async_discover()

                # Should complete without hanging
                assert devices == []

    @pytest.mark.asyncio
    async def test_discover_breaks_when_remaining_time_becomes_negative(self) -> None:
        """Test that discovery loop breaks when remaining time becomes <= 0.

        This tests line 199 in discovery.py where the defensive check
        `if remaining <= 0: break` handles the race condition where time
        passes between the while condition and the remaining calculation.
        """
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            # Mock the event loop's time() to simulate time passing
            # between the while condition check and the remaining calculation
            loop = asyncio.get_event_loop()

            time_call_count = 0

            def mock_time() -> float:
                nonlocal time_call_count
                time_call_count += 1
                # First call is for setting end_time (line 194)
                if time_call_count == 1:
                    return 100.0
                # Second call is for while condition (line 196) - still before end_time
                if time_call_count == 2:
                    return 100.9  # 0.9 < 1.0 timeout, so while condition is True
                # Third call is for remaining calculation (line 197) - now past end_time
                # This makes remaining <= 0, triggering the break on line 199
                return 101.1  # Past end_time (100.0 + 1.0 = 101.0)

            with patch.object(loop, "time", mock_time):
                discovery = ZowietekDiscovery(timeout=1.0)
                devices = await discovery.async_discover()

                # Discovery should complete immediately due to the break
                assert devices == []
                # Verify that time() was called at least 3 times to hit the break
                assert time_call_count >= 3
