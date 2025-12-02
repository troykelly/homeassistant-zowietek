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


class ZowietekVideoData(TypedDict):
    """Video information from async_get_video_info API.

    Contains encoder settings and video configuration as returned
    by the actual ZowieBox API endpoint.
    """

    status: NotRequired[str]
    rsp: NotRequired[str]
    enc_type: NotRequired[str]
    enc_bitrate: NotRequired[int]
    enc_resolution: NotRequired[str]
    enc_framerate: NotRequired[int]


class ZowietekInputSignal(TypedDict):
    """Input signal information from async_get_input_signal API.

    Contains HDMI input signal status as returned by the actual
    ZowieBox API endpoint.
    """

    status: NotRequired[str]
    rsp: NotRequired[str]
    signal: NotRequired[int]
    width: NotRequired[int]
    height: NotRequired[int]
    fps: NotRequired[int]


class ZowietekOutputInfo(TypedDict):
    """Output information from async_get_output_info API.

    Contains HDMI output configuration as returned by the actual
    ZowieBox API endpoint.
    """

    status: NotRequired[str]
    rsp: NotRequired[str]
    format: NotRequired[str]
    loop_out_switch: NotRequired[int]


class ZowietekPublishEntry(TypedDict):
    """Single publish entry from stream publish info."""

    type: NotRequired[str]
    enable: NotRequired[int]
    url: NotRequired[str]


class ZowietekStreamPublish(TypedDict):
    """Stream publish information from async_get_stream_publish_info API.

    Contains list of configured stream publishing destinations.
    """

    publish: list[ZowietekPublishEntry]


class ZowietekNdiConfig(TypedDict):
    """NDI configuration from async_get_ndi_config API.

    Contains NDI streaming configuration as returned by the actual
    ZowieBox API endpoint.
    """

    status: NotRequired[str]
    rsp: NotRequired[str]
    ndi_enable: NotRequired[int]
    ndi_name: NotRequired[str]


class ZowietekSysAttr(TypedDict):
    """System attributes from async_get_sys_attr_info API.

    Contains device identification, firmware version, and serial number.
    """

    SN: NotRequired[str]
    firmware_version: NotRequired[str]
    hardware_version: NotRequired[str]
    model: NotRequired[str]
    manufacturer: NotRequired[str]
    device_name: NotRequired[str]
    ndi_version: NotRequired[str]
    web_version: NotRequired[str]
    app_version: NotRequired[str]
    mcu_version: NotRequired[str]
    isp_version: NotRequired[str]
    chipid: NotRequired[str]


class ZowietekDashboard(TypedDict):
    """Dashboard information from async_get_dashboard_info API.

    Contains uptime and system statistics.
    """

    persistent_time: NotRequired[str]
    device_strat_time: NotRequired[str]
    cpu_temp: NotRequired[float]
    cpu_payload: NotRequired[float]


class ZowietekStreamplayEntry(TypedDict):
    """Single streamplay/decoder source entry.

    Represents a configured playback source in decoder mode.
    """

    index: NotRequired[int]
    switch: NotRequired[int]
    name: NotRequired[str]
    streamtype: NotRequired[int]
    url: NotRequired[str]
    streamplay_status: NotRequired[int]
    bandwidth: NotRequired[int]
    framerate: NotRequired[int]
    width: NotRequired[int]
    height: NotRequired[int]


class ZowietekStreamplayInfo(TypedDict):
    """Streamplay information from async_get_streamplay_info API.

    Contains list of configured decoder playback sources.
    """

    streamplay: list[ZowietekStreamplayEntry]


class ZowietekDecoderStatus(TypedDict):
    """Decoder status from async_get_decoder_status API.

    Contains current decoder state and active source information.
    """

    decoder_state: NotRequired[int]
    active_source: NotRequired[str]
    active_index: NotRequired[int]
    width: NotRequired[int]
    height: NotRequired[int]
    framerate: NotRequired[int]
    bandwidth: NotRequired[int]


class ZowietekNdiSourceEntry(TypedDict):
    """Single NDI source entry.

    Represents a discovered NDI source on the network.
    """

    index: NotRequired[int]
    name: NotRequired[str]
    url: NotRequired[str]


class ZowietekNdiSources(TypedDict):
    """NDI sources from async_get_ndi_sources API.

    Contains list of discovered NDI sources.
    """

    ndi_sources: list[ZowietekNdiSourceEntry]


@dataclass
class ZowietekData:
    """Container for all ZowieBox device data.

    This dataclass aggregates all information types from the device
    for use by the DataUpdateCoordinator. Uses generic dict types
    to accommodate the actual API response structure.
    """

    system: dict[str, str | int]
    video: dict[str, str | int]
    audio: dict[str, str | int]
    stream: dict[str, str | int | list[dict[str, str | int]]]
    network: dict[str, str | int]
    dashboard: dict[str, str | int | float]
    streamplay: dict[str, str | int | list[dict[str, str | int]]]
    decoder_status: dict[str, str | int]
    ndi_sources: list[dict[str, str | int]]
