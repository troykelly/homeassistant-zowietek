"""Tests for the Zowietek media player entity."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zowietek.const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test ZowieBox",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
        unique_id="zowiebox-test-12345",
        version=1,
    )


@pytest.fixture
def mock_device_info() -> dict[str, str]:
    """Return mock device info response."""
    return {
        "status": "00000",
        "rsp": "succeed",
        "devicesn": "zowiebox-test-12345",
        "devicename": "ZowieBox-Studio",
        "softver": "1.2.3",
        "hardver": "2.0",
        "mac": "00:11:22:33:44:55",
        "model": "ZowieBox-4K",
        "uptime": "123456",
    }


@pytest.fixture
def mock_streamplay_info() -> dict[str, list[dict[str, str | int]]]:
    """Return mock streamplay info response (API response format)."""
    return {
        "streamplay": [
            {
                "index": 0,
                "switch": 1,
                "name": "Test Stream 1",
                "streamtype": 1,
                "url": "rtsp://test.stream/live1",
                "streamplay_status": 1,
                "bandwidth": 5000,
                "framerate": 30,
                "width": 1920,
                "height": 1080,
            },
            {
                "index": 1,
                "switch": 0,
                "name": "Test Stream 2",
                "streamtype": 2,
                "url": "rtmp://test.stream/live2",
                "streamplay_status": 0,
                "bandwidth": 0,
                "framerate": 0,
                "width": 0,
                "height": 0,
            },
        ],
    }


@pytest.fixture
def mock_decoder_status_playing() -> dict[str, str | int]:
    """Return mock decoder status when playing (API response format)."""
    return {
        "decoder_state": 1,
        "active_source": "Test Stream 1",
        "active_index": 0,
        "width": 1920,
        "height": 1080,
        "framerate": 30,
        "bandwidth": 5000,
    }


@pytest.fixture
def mock_decoder_status_idle() -> dict[str, str | int]:
    """Return mock decoder status when idle/stopped (API response format)."""
    return {
        "decoder_state": 0,
        "active_source": "",
        "active_index": -1,
        "width": 0,
        "height": 0,
        "framerate": 0,
        "bandwidth": 0,
    }


@pytest.fixture
def mock_ndi_sources() -> dict[str, list[dict[str, str | int]]]:
    """Return mock NDI sources response."""
    return {
        "ndi_sources": [
            {"index": 0, "name": "NDI Source 1", "url": "ndi://source1"},
            {"index": 1, "name": "NDI Source 2", "url": "ndi://source2"},
        ],
    }


def _create_mock_client(
    mock_device_info: dict[str, str],
    mock_streamplay_info: dict[str, list[dict[str, str | int]]],
    mock_decoder_status: dict[str, str | int],
    mock_ndi_sources: dict[str, list[dict[str, str | int]]],
) -> MagicMock:
    """Create a mock client with the specified data."""
    client = MagicMock()
    client.async_get_system_info = AsyncMock(return_value=mock_device_info)
    client.async_get_streamplay_info = AsyncMock(return_value=mock_streamplay_info)
    client.async_get_decoder_status = AsyncMock(return_value=mock_decoder_status)
    client.async_get_ndi_sources = AsyncMock(return_value=mock_ndi_sources)
    client.async_add_decoding_url = AsyncMock()
    client.async_modify_decoding_url = AsyncMock()
    client.async_delete_decoding_url = AsyncMock()
    client.async_select_streamplay_source = AsyncMock()
    client.async_stop_streamplay = AsyncMock()
    client.async_enable_ndi_decoding = AsyncMock()
    client.async_disable_ndi_decoding = AsyncMock()
    client.async_ndi_find = AsyncMock()
    client.close = AsyncMock()
    client.host = "http://192.168.1.100"
    return client


@pytest.fixture
def mock_zowietek_client(
    mock_device_info: dict[str, str],
    mock_streamplay_info: dict[str, list[dict[str, str | int]]],
    mock_decoder_status_playing: dict[str, str | int],
    mock_ndi_sources: dict[str, list[dict[str, str | int]]],
) -> Generator[MagicMock]:
    """Mock ZowietekClient for media player testing."""
    with patch(
        "custom_components.zowietek.coordinator.ZowietekClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value

        # Base methods
        client.async_get_system_info = AsyncMock(return_value=mock_device_info)

        # Video/audio/stream methods for coordinator
        client.async_get_input_signal = AsyncMock(
            return_value={
                "hdmi_signal": 1,
                "audio_signal": 48000,
                "width": 1920,
                "height": 1080,
                "framerate": 60,
                "desc": "1080p60",
            }
        )
        client.async_get_output_info = AsyncMock(
            return_value={
                "switch": 1,
                "format": "1080p60",
                "audio_switch": 1,
                "loop_out_switch": 0,
            }
        )
        client.async_get_venc_info = AsyncMock(
            return_value={
                "venc": [
                    {
                        "venc_chnid": 0,
                        "codec": {"selected_id": 0, "codec_list": ["H.264"]},
                        "bitrate": 12000000,
                        "width": 1920,
                        "height": 1080,
                        "framerate": 60,
                        "desc": "main",
                    },
                ],
            }
        )
        client.async_get_stream_publish_info = AsyncMock(
            return_value={
                "publish": [
                    {"type": "rtmp", "index": 0, "switch": 0, "url": ""},
                    {"type": "srt", "index": 1, "switch": 0, "url": ""},
                ],
            }
        )
        client.async_get_ndi_config = AsyncMock(
            return_value={
                "activate": 1,
                "switch": 1,
                "mode_id": 1,
                "machinename": "ZowieBox-Studio",
                "groups": "Public",
            }
        )
        client.async_get_audio_info = AsyncMock(
            return_value={
                "switch": 1,
                "ai_type": {"selected_id": 0, "ai_type_list": ["LINE IN"]},
                "volume": 100,
            }
        )
        client.async_get_video_info = AsyncMock(
            return_value={
                "status": "00000",
                "rsp": "succeed",
                "input_source": "hdmi",
                "input_resolution": "1920x1080",
                "input_fps": "60",
            }
        )
        client.async_get_network_info = AsyncMock(
            return_value={
                "status": "00000",
                "rsp": "succeed",
                "ip": "192.168.1.100",
                "netmask": "255.255.255.0",
                "gateway": "192.168.1.1",
            }
        )

        # Streamplay methods
        client.async_get_streamplay_info = AsyncMock(return_value=mock_streamplay_info)
        client.async_get_decoder_status = AsyncMock(return_value=mock_decoder_status_playing)
        client.async_get_ndi_sources = AsyncMock(return_value=mock_ndi_sources)

        # Control methods
        client.async_add_decoding_url = AsyncMock()
        client.async_modify_decoding_url = AsyncMock()
        client.async_delete_decoding_url = AsyncMock()
        client.async_select_streamplay_source = AsyncMock()
        client.async_stop_streamplay = AsyncMock()
        client.async_enable_ndi_decoding = AsyncMock()
        client.async_disable_ndi_decoding = AsyncMock()
        client.async_ndi_find = AsyncMock()

        # Write methods for other entities
        client.async_set_audio_volume = AsyncMock()
        client.async_set_encoder_bitrate = AsyncMock()
        client.async_set_ndi_enabled = AsyncMock()
        client.async_set_stream_enabled = AsyncMock()

        client.close = AsyncMock()
        client.host = "http://192.168.1.100"
        yield client


async def _setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Set up the integration for testing."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


class TestMediaPlayerSetup:
    """Tests for media player platform setup."""

    async def test_async_setup_entry_creates_media_player(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test async_setup_entry creates a media player entity."""
        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)

        media_player_entries = [e for e in entries if e.domain == "media_player"]
        assert len(media_player_entries) == 1

    async def test_media_player_entity_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test media player entity is registered in entity registry."""
        await _setup_integration(hass, mock_config_entry)

        entity_registry = er.async_get(hass)
        entity_id = "media_player.zowiebox_studio_decoder"
        entry = entity_registry.async_get(entity_id)
        assert entry is not None

    async def test_media_player_state_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test media player state is available in Home Assistant."""
        await _setup_integration(hass, mock_config_entry)

        state = hass.states.get("media_player.zowiebox_studio_decoder")
        assert state is not None
        assert state.state == MediaPlayerState.PLAYING


class TestZowietekMediaPlayerInit:
    """Tests for ZowietekMediaPlayer initialization."""

    async def test_media_player_inherits_from_zowietek_entity(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test ZowietekMediaPlayer inherits from ZowietekEntity."""
        from custom_components.zowietek.entity import ZowietekEntity
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        assert isinstance(media_player, ZowietekEntity)

    async def test_media_player_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test media player unique_id follows format {unique_id}_decoder."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        assert media_player.unique_id == "zowiebox-test-12345_decoder"

    async def test_media_player_has_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test media player has device_info property from base entity."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)
        device_info = media_player.device_info

        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "zowiebox-test-12345")}
        assert device_info["manufacturer"] == "Zowietek"


class TestMediaPlayerFeatures:
    """Tests for media player supported features."""

    async def test_supported_features(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test media player has correct supported features."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        expected_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )

        assert media_player.supported_features == expected_features


class TestMediaPlayerState:
    """Tests for media player state property."""

    async def test_state_playing_when_decoder_active(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test state is PLAYING when decoder is active."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        # decoder_state: 1 means playing
        assert media_player.state == MediaPlayerState.PLAYING

    async def test_state_idle_when_decoder_stopped(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_decoder_status_idle: dict[str, str | int],
    ) -> None:
        """Test state is IDLE when decoder is stopped."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        # Update mock to return idle status
        mock_zowietek_client.async_get_decoder_status.return_value = mock_decoder_status_idle

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        assert media_player.state == MediaPlayerState.IDLE

    async def test_state_none_when_no_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test state is None when coordinator has no data."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.data = None

        media_player = ZowietekMediaPlayer(coordinator)

        assert media_player.state is None


class TestMediaPlayerSourceList:
    """Tests for media player source list."""

    async def test_source_list_contains_configured_sources(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test source_list contains all configured streamplay sources."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        source_list = media_player.source_list
        assert source_list is not None
        assert "Test Stream 1" in source_list
        assert "Test Stream 2" in source_list

    async def test_source_list_contains_ndi_sources(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test source_list contains discovered NDI sources."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        source_list = media_player.source_list
        assert source_list is not None
        assert "NDI: NDI Source 1" in source_list
        assert "NDI: NDI Source 2" in source_list

    async def test_source_list_empty_when_no_sources(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test source_list is empty when no sources configured."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        # Return empty sources
        mock_zowietek_client.async_get_streamplay_info.return_value = {"streamplay": []}
        mock_zowietek_client.async_get_ndi_sources.return_value = {"ndi_sources": []}

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        source_list = media_player.source_list
        assert source_list == []


class TestMediaPlayerSource:
    """Tests for media player current source."""

    async def test_source_returns_active_source(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test source returns currently active source name."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        assert media_player.source == "Test Stream 1"

    async def test_source_none_when_not_playing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_decoder_status_idle: dict[str, str | int],
    ) -> None:
        """Test source is None when not playing."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        mock_zowietek_client.async_get_decoder_status.return_value = mock_decoder_status_idle

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        assert media_player.source is None


class TestMediaPlayerSelectSource:
    """Tests for media player select source action."""

    async def test_select_source_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test selecting a source calls the correct API method."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_select_source("Test Stream 2")

        mock_zowietek_client.async_select_streamplay_source.assert_called_once_with(1)

    async def test_select_ndi_source_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test selecting an NDI source enables NDI decoding."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_select_source("NDI: NDI Source 1")

        mock_zowietek_client.async_enable_ndi_decoding.assert_called_once_with("NDI Source 1")

    async def test_select_source_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test selecting source requests coordinator refresh."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_select_source("Test Stream 1")

        coordinator.async_request_refresh.assert_called_once()


class TestMediaPlayerStop:
    """Tests for media player stop action."""

    async def test_stop_calls_api(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test stop calls the API to stop playback."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_media_stop()

        mock_zowietek_client.async_stop_streamplay.assert_called_once()

    async def test_stop_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test stop requests coordinator refresh."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_media_stop()

        coordinator.async_request_refresh.assert_called_once()


class TestMediaPlayerPlay:
    """Tests for media player play action."""

    async def test_play_selects_first_source_when_idle(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
        mock_decoder_status_idle: dict[str, str | int],
    ) -> None:
        """Test play selects first available source when idle."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        mock_zowietek_client.async_get_decoder_status.return_value = mock_decoder_status_idle

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_media_play()

        # Should select the first enabled source (index 0)
        mock_zowietek_client.async_select_streamplay_source.assert_called_once_with(0)


class TestMediaPlayerPlayMedia:
    """Tests for media player play_media action."""

    async def test_play_media_adds_url_and_plays(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test play_media adds URL as a source and starts playback."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_play_media(media_type="url", media_id="rtsp://new.stream/live")

        # Should add the URL as a new source
        mock_zowietek_client.async_add_decoding_url.assert_called_once()
        call_args = mock_zowietek_client.async_add_decoding_url.call_args
        assert call_args[1]["url"] == "rtsp://new.stream/live"

    async def test_play_media_uses_ha_source_name(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test play_media always uses 'Home Assistant' as source name."""
        from custom_components.zowietek.media_player import (
            HA_SOURCE_NAME,
            ZowietekMediaPlayer,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        # Even with extra title, we use HA_SOURCE_NAME
        await media_player.async_play_media(
            media_type="url",
            media_id="rtsp://new.stream/live",
            extra={"title": "Custom Stream Name"},
        )

        call_args = mock_zowietek_client.async_add_decoding_url.call_args
        # Source name should be HA_SOURCE_NAME, not the custom title
        assert call_args[1]["name"] == HA_SOURCE_NAME

    async def test_play_media_requests_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test play_media requests coordinator refresh."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.async_request_refresh = AsyncMock()
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_play_media(media_type="url", media_id="rtsp://new.stream/live")

        coordinator.async_request_refresh.assert_called_once()

    async def test_play_media_modifies_existing_ha_source(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test play_media modifies existing HA source instead of adding a new one."""
        from custom_components.zowietek.media_player import (
            HA_SOURCE_NAME,
            ZowietekMediaPlayer,
        )

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        # Include an existing "Home Assistant" source in the streamplay sources
        coordinator.data.streamplay["sources"].append(
            {
                "index": 5,
                "name": HA_SOURCE_NAME,
                "url": "rtsp://old.stream/live",
                "switch": 0,
            }
        )
        media_player = ZowietekMediaPlayer(coordinator)

        await media_player.async_play_media(
            media_type="url",
            media_id="rtsp://new.stream/live",
        )

        # Should modify existing source, not add a new one
        mock_zowietek_client.async_add_decoding_url.assert_not_called()
        mock_zowietek_client.async_modify_decoding_url.assert_called_once()
        call_args = mock_zowietek_client.async_modify_decoding_url.call_args
        assert call_args[1]["index"] == 5
        assert call_args[1]["name"] == HA_SOURCE_NAME
        assert call_args[1]["url"] == "rtsp://new.stream/live"
        assert call_args[1]["switch"] is True

    async def test_play_media_switches_to_existing_url(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test play_media switches to existing source if URL already exists."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        # The default mock data has sources with URLs, let's use one of them
        # Add a source with a specific URL we'll request
        coordinator.data.streamplay["sources"].append(
            {
                "index": 7,
                "name": "Existing Camera",
                "url": "rtsp://existing.camera/stream",
                "switch": 0,
            }
        )
        media_player = ZowietekMediaPlayer(coordinator)

        # Request the same URL that already exists
        await media_player.async_play_media(
            media_type="url",
            media_id="rtsp://existing.camera/stream",
        )

        # Should just switch to the existing source, not add or modify
        mock_zowietek_client.async_add_decoding_url.assert_not_called()
        mock_zowietek_client.async_modify_decoding_url.assert_not_called()
        mock_zowietek_client.async_select_streamplay_source.assert_called_once_with(7)


class TestMediaPlayerExtraAttributes:
    """Tests for media player extra state attributes."""

    async def test_extra_state_attributes_includes_resolution(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test extra attributes include video resolution."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        attrs = media_player.extra_state_attributes
        assert attrs is not None
        assert attrs.get("video_resolution") == "1920x1080"

    async def test_extra_state_attributes_includes_framerate(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test extra attributes include framerate."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        attrs = media_player.extra_state_attributes
        assert attrs is not None
        assert attrs.get("framerate") == 30

    async def test_extra_state_attributes_includes_bandwidth(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test extra attributes include bandwidth."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        attrs = media_player.extra_state_attributes
        assert attrs is not None
        assert attrs.get("bandwidth_kbps") == 5000


class TestMediaPlayerAvailability:
    """Tests for media player availability."""

    async def test_available_when_coordinator_has_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test media player is available when coordinator has data."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        assert media_player.available is True

    async def test_unavailable_when_coordinator_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test media player is unavailable when coordinator update fails."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        coordinator.last_update_success = False

        media_player = ZowietekMediaPlayer(coordinator)

        assert media_player.available is False


class TestMediaPlayerErrorHandling:
    """Tests for error handling in media player."""

    async def test_select_source_api_error_raises_ha_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test select_source raises HomeAssistantError when API fails."""
        from homeassistant.exceptions import HomeAssistantError

        from custom_components.zowietek.exceptions import ZowietekApiError
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        # Make API call raise an error
        mock_zowietek_client.async_select_streamplay_source.side_effect = ZowietekApiError(
            "Device not responding", "00000"
        )

        media_player = ZowietekMediaPlayer(coordinator)

        with pytest.raises(HomeAssistantError) as exc_info:
            await media_player.async_select_source("Test Stream 1")

        assert "Failed to select source" in str(exc_info.value)

    async def test_stop_api_error_raises_ha_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test stop raises HomeAssistantError when API fails."""
        from homeassistant.exceptions import HomeAssistantError

        from custom_components.zowietek.exceptions import ZowietekApiError
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        mock_zowietek_client.async_stop_streamplay.side_effect = ZowietekApiError(
            "Device not responding", "00000"
        )

        media_player = ZowietekMediaPlayer(coordinator)

        with pytest.raises(HomeAssistantError) as exc_info:
            await media_player.async_media_stop()

        assert "Failed to stop playback" in str(exc_info.value)

    async def test_play_media_api_error_raises_ha_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test play_media raises HomeAssistantError when API fails."""
        from homeassistant.exceptions import HomeAssistantError

        from custom_components.zowietek.exceptions import ZowietekApiError
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data

        mock_zowietek_client.async_add_decoding_url.side_effect = ZowietekApiError(
            "Failed to add source", "00000"
        )

        media_player = ZowietekMediaPlayer(coordinator)

        with pytest.raises(HomeAssistantError) as exc_info:
            await media_player.async_play_media(media_type="url", media_id="rtsp://test/stream")

        assert "Failed to play media" in str(exc_info.value)


class TestMediaPlayerIcon:
    """Tests for media player icon."""

    async def test_icon_is_video_input_antenna(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_zowietek_client: MagicMock,
    ) -> None:
        """Test media player has correct icon."""
        from custom_components.zowietek.media_player import ZowietekMediaPlayer

        await _setup_integration(hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data
        media_player = ZowietekMediaPlayer(coordinator)

        assert media_player.icon == "mdi:video-input-antenna"
