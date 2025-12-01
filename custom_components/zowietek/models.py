"""TypedDict models for ZowieBox API responses.

This module defines type-safe structures for all ZowieBox API responses,
ensuring proper type hints and IDE autocompletion support throughout
the integration.

Note: This module intentionally does NOT use `from __future__ import annotations`
because TypedDict requires evaluated type hints at runtime to properly distinguish
required vs optional keys (NotRequired). The PEP 563 deferred evaluation makes
all annotations ForwardRef strings, which breaks TypedDict's introspection.
"""

from dataclasses import dataclass
from typing import NotRequired, TypedDict


class ZowietekSystemInfo(TypedDict):
    """System information response from ZowieBox API.

    Contains device identification and version information.
    The status and rsp fields are always present in API responses.
    """

    status: str
    rsp: str
    device_name: NotRequired[str]
    device_serial: NotRequired[str]
    firmware_version: NotRequired[str]
    hardware_version: NotRequired[str]
    mac_address: NotRequired[str]
    model: NotRequired[str]


class ZowietekVideoInfo(TypedDict):
    """Video information response from ZowieBox API.

    Contains input signal detection and output configuration.
    The status and rsp fields are always present in API responses.
    """

    status: str
    rsp: str
    input_signal: NotRequired[bool]
    input_width: NotRequired[int]
    input_height: NotRequired[int]
    input_framerate: NotRequired[int]
    output_format: NotRequired[str]
    loop_out_enabled: NotRequired[bool]


class ZowietekAudioInfo(TypedDict):
    """Audio information response from ZowieBox API.

    Contains audio configuration and status information.
    The status and rsp fields are always present in API responses.
    """

    status: str
    rsp: str
    audio_enabled: NotRequired[bool]
    input_type: NotRequired[str]
    codec: NotRequired[str]
    sample_rate: NotRequired[int]
    bitrate: NotRequired[int]
    volume: NotRequired[int]


class ZowietekStreamInfo(TypedDict):
    """Stream information response from ZowieBox API.

    Contains NDI, RTMP, and SRT streaming configuration.
    The status and rsp fields are always present in API responses.
    """

    status: str
    rsp: str
    ndi_enabled: NotRequired[bool]
    ndi_name: NotRequired[str]
    rtmp_enabled: NotRequired[bool]
    rtmp_url: NotRequired[str]
    srt_enabled: NotRequired[bool]
    srt_url: NotRequired[str]


class ZowietekNetworkInfo(TypedDict):
    """Network information response from ZowieBox API.

    Contains network configuration including IP settings.
    The status and rsp fields are always present in API responses.
    """

    status: str
    rsp: str
    ip_address: NotRequired[str]
    netmask: NotRequired[str]
    gateway: NotRequired[str]
    dhcp_enabled: NotRequired[bool]
    mac_address: NotRequired[str]


@dataclass
class ZowietekData:
    """Container for all ZowieBox device data.

    This dataclass aggregates all information types from the device
    for use by the DataUpdateCoordinator.
    """

    system: ZowietekSystemInfo
    video: ZowietekVideoInfo
    audio: ZowietekAudioInfo
    stream: ZowietekStreamInfo
    network: ZowietekNetworkInfo
