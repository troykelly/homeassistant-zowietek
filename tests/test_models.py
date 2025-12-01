"""Tests for Zowietek TypedDict models."""

from __future__ import annotations

from dataclasses import fields
from typing import get_type_hints

from custom_components.zowietek.models import (
    ZowietekAudioInfo,
    ZowietekData,
    ZowietekNetworkInfo,
    ZowietekStreamInfo,
    ZowietekSystemInfo,
    ZowietekVideoInfo,
)


class TestZowietekSystemInfo:
    """Tests for ZowietekSystemInfo TypedDict."""

    def test_system_info_is_typed_dict(self) -> None:
        """Test that ZowietekSystemInfo is a TypedDict."""
        # TypedDicts have __required_keys__ and __optional_keys__
        assert hasattr(ZowietekSystemInfo, "__required_keys__")
        assert hasattr(ZowietekSystemInfo, "__optional_keys__")

    def test_system_info_has_required_status_field(self) -> None:
        """Test that status is a required field."""
        assert "status" in ZowietekSystemInfo.__required_keys__

    def test_system_info_has_required_rsp_field(self) -> None:
        """Test that rsp is a required field."""
        assert "rsp" in ZowietekSystemInfo.__required_keys__

    def test_system_info_has_optional_device_name_field(self) -> None:
        """Test that device_name is an optional field."""
        assert "device_name" in ZowietekSystemInfo.__optional_keys__

    def test_system_info_has_optional_device_serial_field(self) -> None:
        """Test that device_serial is an optional field."""
        assert "device_serial" in ZowietekSystemInfo.__optional_keys__

    def test_system_info_has_optional_firmware_version_field(self) -> None:
        """Test that firmware_version is an optional field."""
        assert "firmware_version" in ZowietekSystemInfo.__optional_keys__

    def test_system_info_has_optional_hardware_version_field(self) -> None:
        """Test that hardware_version is an optional field."""
        assert "hardware_version" in ZowietekSystemInfo.__optional_keys__

    def test_system_info_has_optional_mac_address_field(self) -> None:
        """Test that mac_address is an optional field."""
        assert "mac_address" in ZowietekSystemInfo.__optional_keys__

    def test_system_info_has_optional_model_field(self) -> None:
        """Test that model is an optional field."""
        assert "model" in ZowietekSystemInfo.__optional_keys__

    def test_system_info_can_be_instantiated_with_required_fields(self) -> None:
        """Test that ZowietekSystemInfo can be created with only required fields."""
        info: ZowietekSystemInfo = {
            "status": "00000",
            "rsp": "succeed",
        }
        assert info["status"] == "00000"
        assert info["rsp"] == "succeed"

    def test_system_info_can_be_instantiated_with_all_fields(self) -> None:
        """Test that ZowietekSystemInfo can be created with all fields."""
        info: ZowietekSystemInfo = {
            "status": "00000",
            "rsp": "succeed",
            "device_name": "ZowieBox-Test",
            "device_serial": "ABC123",
            "firmware_version": "1.0.0",
            "hardware_version": "2.0",
            "mac_address": "00:11:22:33:44:55",
            "model": "ZowieBox 4K",
        }
        assert info["device_name"] == "ZowieBox-Test"
        assert info["device_serial"] == "ABC123"


class TestZowietekVideoInfo:
    """Tests for ZowietekVideoInfo TypedDict."""

    def test_video_info_is_typed_dict(self) -> None:
        """Test that ZowietekVideoInfo is a TypedDict."""
        assert hasattr(ZowietekVideoInfo, "__required_keys__")
        assert hasattr(ZowietekVideoInfo, "__optional_keys__")

    def test_video_info_has_required_status_field(self) -> None:
        """Test that status is a required field."""
        assert "status" in ZowietekVideoInfo.__required_keys__

    def test_video_info_has_required_rsp_field(self) -> None:
        """Test that rsp is a required field."""
        assert "rsp" in ZowietekVideoInfo.__required_keys__

    def test_video_info_has_optional_input_signal_field(self) -> None:
        """Test that input_signal is an optional field."""
        assert "input_signal" in ZowietekVideoInfo.__optional_keys__

    def test_video_info_has_optional_input_width_field(self) -> None:
        """Test that input_width is an optional field."""
        assert "input_width" in ZowietekVideoInfo.__optional_keys__

    def test_video_info_has_optional_input_height_field(self) -> None:
        """Test that input_height is an optional field."""
        assert "input_height" in ZowietekVideoInfo.__optional_keys__

    def test_video_info_has_optional_input_framerate_field(self) -> None:
        """Test that input_framerate is an optional field."""
        assert "input_framerate" in ZowietekVideoInfo.__optional_keys__

    def test_video_info_has_optional_output_format_field(self) -> None:
        """Test that output_format is an optional field."""
        assert "output_format" in ZowietekVideoInfo.__optional_keys__

    def test_video_info_has_optional_loop_out_enabled_field(self) -> None:
        """Test that loop_out_enabled is an optional field."""
        assert "loop_out_enabled" in ZowietekVideoInfo.__optional_keys__

    def test_video_info_can_be_instantiated(self) -> None:
        """Test that ZowietekVideoInfo can be created."""
        info: ZowietekVideoInfo = {
            "status": "00000",
            "rsp": "succeed",
            "input_signal": True,
            "input_width": 1920,
            "input_height": 1080,
            "input_framerate": 60,
        }
        assert info["input_width"] == 1920


class TestZowietekAudioInfo:
    """Tests for ZowietekAudioInfo TypedDict."""

    def test_audio_info_is_typed_dict(self) -> None:
        """Test that ZowietekAudioInfo is a TypedDict."""
        assert hasattr(ZowietekAudioInfo, "__required_keys__")
        assert hasattr(ZowietekAudioInfo, "__optional_keys__")

    def test_audio_info_has_required_status_field(self) -> None:
        """Test that status is a required field."""
        assert "status" in ZowietekAudioInfo.__required_keys__

    def test_audio_info_has_required_rsp_field(self) -> None:
        """Test that rsp is a required field."""
        assert "rsp" in ZowietekAudioInfo.__required_keys__

    def test_audio_info_has_optional_audio_enabled_field(self) -> None:
        """Test that audio_enabled is an optional field."""
        assert "audio_enabled" in ZowietekAudioInfo.__optional_keys__

    def test_audio_info_has_optional_input_type_field(self) -> None:
        """Test that input_type is an optional field."""
        assert "input_type" in ZowietekAudioInfo.__optional_keys__

    def test_audio_info_has_optional_codec_field(self) -> None:
        """Test that codec is an optional field."""
        assert "codec" in ZowietekAudioInfo.__optional_keys__

    def test_audio_info_has_optional_sample_rate_field(self) -> None:
        """Test that sample_rate is an optional field."""
        assert "sample_rate" in ZowietekAudioInfo.__optional_keys__

    def test_audio_info_has_optional_bitrate_field(self) -> None:
        """Test that bitrate is an optional field."""
        assert "bitrate" in ZowietekAudioInfo.__optional_keys__

    def test_audio_info_has_optional_volume_field(self) -> None:
        """Test that volume is an optional field."""
        assert "volume" in ZowietekAudioInfo.__optional_keys__

    def test_audio_info_can_be_instantiated(self) -> None:
        """Test that ZowietekAudioInfo can be created."""
        info: ZowietekAudioInfo = {
            "status": "00000",
            "rsp": "succeed",
            "audio_enabled": True,
            "volume": 80,
        }
        assert info["volume"] == 80


class TestZowietekStreamInfo:
    """Tests for ZowietekStreamInfo TypedDict."""

    def test_stream_info_is_typed_dict(self) -> None:
        """Test that ZowietekStreamInfo is a TypedDict."""
        assert hasattr(ZowietekStreamInfo, "__required_keys__")
        assert hasattr(ZowietekStreamInfo, "__optional_keys__")

    def test_stream_info_has_required_status_field(self) -> None:
        """Test that status is a required field."""
        assert "status" in ZowietekStreamInfo.__required_keys__

    def test_stream_info_has_required_rsp_field(self) -> None:
        """Test that rsp is a required field."""
        assert "rsp" in ZowietekStreamInfo.__required_keys__

    def test_stream_info_has_optional_ndi_enabled_field(self) -> None:
        """Test that ndi_enabled is an optional field."""
        assert "ndi_enabled" in ZowietekStreamInfo.__optional_keys__

    def test_stream_info_has_optional_ndi_name_field(self) -> None:
        """Test that ndi_name is an optional field."""
        assert "ndi_name" in ZowietekStreamInfo.__optional_keys__

    def test_stream_info_has_optional_rtmp_enabled_field(self) -> None:
        """Test that rtmp_enabled is an optional field."""
        assert "rtmp_enabled" in ZowietekStreamInfo.__optional_keys__

    def test_stream_info_has_optional_rtmp_url_field(self) -> None:
        """Test that rtmp_url is an optional field."""
        assert "rtmp_url" in ZowietekStreamInfo.__optional_keys__

    def test_stream_info_has_optional_srt_enabled_field(self) -> None:
        """Test that srt_enabled is an optional field."""
        assert "srt_enabled" in ZowietekStreamInfo.__optional_keys__

    def test_stream_info_has_optional_srt_url_field(self) -> None:
        """Test that srt_url is an optional field."""
        assert "srt_url" in ZowietekStreamInfo.__optional_keys__

    def test_stream_info_can_be_instantiated(self) -> None:
        """Test that ZowietekStreamInfo can be created."""
        info: ZowietekStreamInfo = {
            "status": "00000",
            "rsp": "succeed",
            "ndi_enabled": True,
            "ndi_name": "ZowieBox-NDI",
        }
        assert info["ndi_enabled"] is True


class TestZowietekNetworkInfo:
    """Tests for ZowietekNetworkInfo TypedDict."""

    def test_network_info_is_typed_dict(self) -> None:
        """Test that ZowietekNetworkInfo is a TypedDict."""
        assert hasattr(ZowietekNetworkInfo, "__required_keys__")
        assert hasattr(ZowietekNetworkInfo, "__optional_keys__")

    def test_network_info_has_required_status_field(self) -> None:
        """Test that status is a required field."""
        assert "status" in ZowietekNetworkInfo.__required_keys__

    def test_network_info_has_required_rsp_field(self) -> None:
        """Test that rsp is a required field."""
        assert "rsp" in ZowietekNetworkInfo.__required_keys__

    def test_network_info_has_optional_ip_address_field(self) -> None:
        """Test that ip_address is an optional field."""
        assert "ip_address" in ZowietekNetworkInfo.__optional_keys__

    def test_network_info_has_optional_netmask_field(self) -> None:
        """Test that netmask is an optional field."""
        assert "netmask" in ZowietekNetworkInfo.__optional_keys__

    def test_network_info_has_optional_gateway_field(self) -> None:
        """Test that gateway is an optional field."""
        assert "gateway" in ZowietekNetworkInfo.__optional_keys__

    def test_network_info_has_optional_dhcp_enabled_field(self) -> None:
        """Test that dhcp_enabled is an optional field."""
        assert "dhcp_enabled" in ZowietekNetworkInfo.__optional_keys__

    def test_network_info_has_optional_mac_address_field(self) -> None:
        """Test that mac_address is an optional field."""
        assert "mac_address" in ZowietekNetworkInfo.__optional_keys__

    def test_network_info_can_be_instantiated(self) -> None:
        """Test that ZowietekNetworkInfo can be created."""
        info: ZowietekNetworkInfo = {
            "status": "00000",
            "rsp": "succeed",
            "ip_address": "192.168.1.100",
            "netmask": "255.255.255.0",
            "gateway": "192.168.1.1",
        }
        assert info["ip_address"] == "192.168.1.100"


class TestZowietekData:
    """Tests for ZowietekData dataclass."""

    def test_zowietek_data_is_dataclass(self) -> None:
        """Test that ZowietekData is a dataclass."""
        # Dataclasses have __dataclass_fields__
        assert hasattr(ZowietekData, "__dataclass_fields__")

    def test_zowietek_data_has_system_field(self) -> None:
        """Test that ZowietekData has a system field."""
        field_names = [f.name for f in fields(ZowietekData)]
        assert "system" in field_names

    def test_zowietek_data_has_video_field(self) -> None:
        """Test that ZowietekData has a video field."""
        field_names = [f.name for f in fields(ZowietekData)]
        assert "video" in field_names

    def test_zowietek_data_has_audio_field(self) -> None:
        """Test that ZowietekData has an audio field."""
        field_names = [f.name for f in fields(ZowietekData)]
        assert "audio" in field_names

    def test_zowietek_data_has_stream_field(self) -> None:
        """Test that ZowietekData has a stream field."""
        field_names = [f.name for f in fields(ZowietekData)]
        assert "stream" in field_names

    def test_zowietek_data_has_network_field(self) -> None:
        """Test that ZowietekData has a network field."""
        field_names = [f.name for f in fields(ZowietekData)]
        assert "network" in field_names

    def test_zowietek_data_can_be_instantiated(self) -> None:
        """Test that ZowietekData can be created with all info types."""
        system: ZowietekSystemInfo = {
            "status": "00000",
            "rsp": "succeed",
            "device_name": "ZowieBox-Test",
        }
        video: ZowietekVideoInfo = {
            "status": "00000",
            "rsp": "succeed",
            "input_width": 1920,
            "input_height": 1080,
        }
        audio: ZowietekAudioInfo = {
            "status": "00000",
            "rsp": "succeed",
            "volume": 80,
        }
        stream: ZowietekStreamInfo = {
            "status": "00000",
            "rsp": "succeed",
            "ndi_enabled": True,
        }
        network: ZowietekNetworkInfo = {
            "status": "00000",
            "rsp": "succeed",
            "ip_address": "192.168.1.100",
        }

        data = ZowietekData(
            system=system,
            video=video,
            audio=audio,
            stream=stream,
            network=network,
        )

        assert data.system["device_name"] == "ZowieBox-Test"
        assert data.video["input_width"] == 1920
        assert data.audio["volume"] == 80
        assert data.stream["ndi_enabled"] is True
        assert data.network["ip_address"] == "192.168.1.100"

    def test_zowietek_data_fields_have_correct_types(self) -> None:
        """Test that ZowietekData fields have the correct type annotations."""
        hints = get_type_hints(ZowietekData)
        assert hints["system"] == ZowietekSystemInfo
        assert hints["video"] == ZowietekVideoInfo
        assert hints["audio"] == ZowietekAudioInfo
        assert hints["stream"] == ZowietekStreamInfo
        assert hints["network"] == ZowietekNetworkInfo


class TestTypeAnnotations:
    """Tests to verify no Any types are used."""

    def test_system_info_type_hints_have_no_any(self) -> None:
        """Test that ZowietekSystemInfo has no Any type hints."""
        hints = get_type_hints(ZowietekSystemInfo)
        for field_name, field_type in hints.items():
            # NotRequired[str] unwraps to str in get_type_hints
            assert field_type is not type(None), f"{field_name} should not be None type"
            # Check the string representation doesn't contain 'Any'
            type_str = str(field_type)
            assert "Any" not in type_str, f"{field_name} should not use Any type"

    def test_video_info_type_hints_have_no_any(self) -> None:
        """Test that ZowietekVideoInfo has no Any type hints."""
        hints = get_type_hints(ZowietekVideoInfo)
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert "Any" not in type_str, f"{field_name} should not use Any type"

    def test_audio_info_type_hints_have_no_any(self) -> None:
        """Test that ZowietekAudioInfo has no Any type hints."""
        hints = get_type_hints(ZowietekAudioInfo)
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert "Any" not in type_str, f"{field_name} should not use Any type"

    def test_stream_info_type_hints_have_no_any(self) -> None:
        """Test that ZowietekStreamInfo has no Any type hints."""
        hints = get_type_hints(ZowietekStreamInfo)
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert "Any" not in type_str, f"{field_name} should not use Any type"

    def test_network_info_type_hints_have_no_any(self) -> None:
        """Test that ZowietekNetworkInfo has no Any type hints."""
        hints = get_type_hints(ZowietekNetworkInfo)
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert "Any" not in type_str, f"{field_name} should not use Any type"

    def test_zowietek_data_type_hints_have_no_any(self) -> None:
        """Test that ZowietekData has no Any type hints."""
        hints = get_type_hints(ZowietekData)
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert "Any" not in type_str, f"{field_name} should not use Any type"
