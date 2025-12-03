# Advanced Configuration

This guide covers advanced features, services, device triggers, and technical details for power users.

## Table of Contents

- [Configuration Options](#configuration-options)
- [Entity Reference](#entity-reference)
- [Services](#services)
- [Device Triggers](#device-triggers)
- [Media Player (Decoder Mode)](#media-player-decoder-mode)
- [go2rtc Integration](#go2rtc-integration)
- [Device Discovery](#device-discovery)
- [Diagnostics](#diagnostics)

---

## Configuration Options

After adding a device, configure options via:

**Settings** → **Devices & Services** → **Zowietek** → **Configure**

| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| Update interval | Polling frequency (seconds) | 30 | 10-300 |
| Use go2rtc | Enable stream conversion for incompatible URLs | On | On/Off |

### Reconfiguration

To update device host or credentials:

1. Go to the device's integration page
2. Click **Reconfigure**
3. Enter updated settings
4. Submit

---

## Entity Reference

### Sensors

| Entity ID Pattern | Description | Unit |
|-------------------|-------------|------|
| `sensor.{device}_video_resolution` | Current encoding resolution | - |
| `sensor.{device}_frame_rate` | Encoding frame rate | fps |
| `sensor.{device}_stream_bitrate` | Encoding bitrate | bps |
| `sensor.{device}_encoder_type` | Video codec (H.264/H.265) | - |
| `sensor.{device}_ndi_name` | Configured NDI stream name | - |
| `sensor.{device}_output_format` | HDMI output format | - |
| `sensor.{device}_firmware_version` | Device firmware | - |
| `sensor.{device}_hardware_version` | Hardware revision | - |
| `sensor.{device}_serial_number` | Device serial number | - |
| `sensor.{device}_uptime` | Time since last reboot | - |
| `sensor.{device}_cpu_temperature` | CPU temperature | °C |
| `sensor.{device}_cpu_usage` | CPU utilization | % |

### Binary Sensors

| Entity ID Pattern | Description | On State |
|-------------------|-------------|----------|
| `binary_sensor.{device}_streaming` | Any stream active | Streaming |
| `binary_sensor.{device}_video_input` | HDMI signal detected | Signal present |
| `binary_sensor.{device}_ndi_enabled` | NDI output enabled | Enabled |
| `binary_sensor.{device}_rtmp_enabled` | RTMP output enabled | Enabled |
| `binary_sensor.{device}_srt_enabled` | SRT output enabled | Enabled |

### Switches

| Entity ID Pattern | Description |
|-------------------|-------------|
| `switch.{device}_ndi_stream` | Enable/disable NDI|HX output |
| `switch.{device}_rtmp_stream` | Enable/disable RTMP streaming |
| `switch.{device}_srt_stream` | Enable/disable SRT streaming |

### Select Entities

| Entity ID Pattern | Description | Options |
|-------------------|-------------|---------|
| `select.{device}_encoder_type` | Video codec | H.264, H.265 |
| `select.{device}_output_format` | HDMI output resolution | 720p50, 720p60, 1080p50, 1080p60, 2160p30, etc. |

### Number Entities

| Entity ID Pattern | Description | Range |
|-------------------|-------------|-------|
| `number.{device}_audio_volume` | Audio input level | 0-100% |
| `number.{device}_stream_bitrate` | Encoding bitrate | 1-50 Mbps |

### Button Entities

| Entity ID Pattern | Description |
|-------------------|-------------|
| `button.{device}_reboot` | Restart the device |
| `button.{device}_refresh` | Force data refresh |

### Media Player (Decoder)

| Entity ID Pattern | Description |
|-------------------|-------------|
| `media_player.{device}_decoder` | Decoder playback control |

---

## Services

### zowietek.set_ndi_settings

Configure NDI stream name and group.

**Parameters:**

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `device_id` | Yes | string | Device ID from HA |
| `name` | Yes | string | NDI stream name |
| `group` | No | string | NDI group name |

**Example:**

```yaml
service: zowietek.set_ndi_settings
data:
  device_id: "abc123def456"
  name: "Studio-Camera-1"
  group: "Production"
```

**Automation Example:**

```yaml
alias: Set NDI Name Based on Room
trigger:
  - platform: state
    entity_id: input_select.current_studio
action:
  - service: zowietek.set_ndi_settings
    data:
      device_id: "abc123def456"
      name: "{{ states('input_select.current_studio') }}-Camera"
```

### zowietek.set_rtmp_url

Configure RTMP streaming destination.

**Parameters:**

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `device_id` | Yes | string | Device ID from HA |
| `url` | Yes | string | RTMP server URL |
| `key` | No | string | Stream key |

**Example:**

```yaml
service: zowietek.set_rtmp_url
data:
  device_id: "abc123def456"
  url: "rtmp://live.example.com/live"
  key: "your-stream-key"
```

**Automation Example - Stream to YouTube:**

```yaml
alias: Start YouTube Stream
sequence:
  - service: zowietek.set_rtmp_url
    data:
      device_id: "abc123def456"
      url: "rtmp://a.rtmp.youtube.com/live2"
      key: !secret youtube_stream_key
  - delay: "00:00:02"
  - service: switch.turn_on
    target:
      entity_id: switch.zowiebox_rtmp_stream
```

### zowietek.set_srt_settings

Configure SRT streaming parameters.

**Parameters:**

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `device_id` | Yes | string | Device ID from HA |
| `port` | Yes | integer | SRT port (1-65535) |
| `latency` | No | integer | Latency in ms (20-8000) |
| `passphrase` | No | string | Encryption passphrase |

**Example:**

```yaml
service: zowietek.set_srt_settings
data:
  device_id: "abc123def456"
  port: 9000
  latency: 120
  passphrase: "secure-passphrase"
```

---

## Device Triggers

Use these in automations with the Device trigger platform:

| Trigger Type | Description | Fires When |
|--------------|-------------|------------|
| `stream_started` | Stream output activated | Any stream (NDI/RTMP/SRT) starts |
| `stream_stopped` | All streams stopped | All stream outputs stop |
| `video_input_detected` | Video signal found | HDMI input signal detected |
| `video_input_lost` | Video signal lost | HDMI input signal lost |

**Automation Example:**

```yaml
alias: Alert on Video Loss During Live Show
trigger:
  - platform: device
    domain: zowietek
    device_id: "abc123def456"
    type: video_input_lost
condition:
  - condition: state
    entity_id: input_boolean.live_show_active
    state: "on"
action:
  - service: notify.broadcast
    data:
      message: "CRITICAL: Video input lost during live show!"
  - service: light.turn_on
    target:
      entity_id: light.studio_alert
    data:
      color_name: red
      flash: long
```

**Stream Monitoring:**

```yaml
alias: Log Streaming Sessions
trigger:
  - platform: device
    domain: zowietek
    device_id: "abc123def456"
    type: stream_started
    id: started
  - platform: device
    domain: zowietek
    device_id: "abc123def456"
    type: stream_stopped
    id: stopped
action:
  - service: logbook.log
    data:
      name: ZowieBox
      message: >
        {% if trigger.id == 'started' %}
          Streaming started
        {% else %}
          Streaming stopped
        {% endif %}
```

---

## Media Player (Decoder Mode)

The media player entity provides full decoder control.

### States

| State | Description |
|-------|-------------|
| `playing` | Actively playing a stream |
| `idle` | Ready but not playing |
| `standby` | Device in low-power mode |
| `unavailable` | Device unreachable |

### Source Selection

Sources include:
- Configured stream sources on the device
- Discovered NDI sources on the network
- Custom "Home Assistant" source for play_media

**Switch Source:**

```yaml
service: media_player.select_source
target:
  entity_id: media_player.zowiebox_decoder
data:
  source: "Studio-Camera-1 (NDI)"
```

### Play Media

Play arbitrary stream URLs:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.zowiebox_decoder
data:
  media_content_type: url
  media_content_id: "rtsp://192.168.1.50:554/stream"
```

**Supported URL formats:**

| Protocol | Format | Native Support |
|----------|--------|----------------|
| RTSP | `rtsp://host:port/path` | Yes |
| RTMP | `rtmp://host/app/key` | Yes |
| SRT | `srt://host:port` | Yes |
| HTTP | `http://host/stream` | Yes |
| HTTPS | `https://host/stream` | Yes |
| HLS | `http://host/playlist.m3u8` | Via go2rtc |
| DASH | `http://host/manifest.mpd` | Via go2rtc |

### Playback Control

```yaml
# Stop playback
service: media_player.media_stop
target:
  entity_id: media_player.zowiebox_decoder

# Enter standby
service: media_player.turn_off
target:
  entity_id: media_player.zowiebox_decoder

# Wake from standby
service: media_player.turn_on
target:
  entity_id: media_player.zowiebox_decoder
```

---

## go2rtc Integration

The integration uses Home Assistant's built-in go2rtc for stream conversion.

### What It Does

- Converts HLS/DASH streams to RTSP for ZowieBox playback
- Enables playback of Home Assistant camera entities
- Handles incompatible stream formats transparently

### When It's Used

| URL Type | Conversion |
|----------|------------|
| `rtsp://`, `rtmp://`, `srt://` | Direct (no conversion) |
| `.m3u8` (HLS) | Converted via go2rtc |
| `.mpd` (DASH) | Converted via go2rtc |
| `camera.entity_id` | Converted via go2rtc |

### Playing Home Assistant Cameras

```yaml
service: media_player.play_media
target:
  entity_id: media_player.zowiebox_decoder
data:
  media_content_type: camera
  media_content_id: "camera.front_door"
```

### Disabling go2rtc

If you experience issues, disable go2rtc conversion:

1. Go to **Settings** → **Devices & Services** → **Zowietek**
2. Click **Configure**
3. Toggle off **Use go2rtc for stream conversion**
4. Submit

### Technical Details

- go2rtc API port: `11984`
- go2rtc RTSP output port: `18554`
- Stream TTL: 300 seconds (auto-cleanup)
- Streams are reused for repeated access

---

## Device Discovery

### Discovery Protocol

ZowieBox uses proprietary UDP multicast discovery:

| Parameter | Value |
|-----------|-------|
| Protocol | UDP |
| Multicast Address | `224.170.1.242` |
| Port | `21007` |
| IP Version | IPv4 only |

### Network Requirements

For auto-discovery to work:
- Home Assistant must be on the same network/VLAN as devices
- Network must allow multicast traffic
- Firewall must permit UDP port 21007

### Manual Configuration

If discovery fails, configure devices manually:
1. Find your device's IP address (from router or device web UI)
2. During setup, choose "Enter manually"
3. Enter the IP address or hostname

### Discovery Troubleshooting

| Issue | Solution |
|-------|----------|
| No devices found | Use manual IP entry |
| Different VLANs | Enable multicast routing or use manual entry |
| Firewall blocking | Allow UDP 21007 to multicast 224.170.1.242 |
| WiFi isolation | Connect via wired network or disable isolation |

---

## Diagnostics

Download device diagnostics for troubleshooting:

1. Go to **Settings** → **Devices & Services** → **Zowietek**
2. Click on your device
3. Click **Download diagnostics**

The download includes:
- Device configuration (credentials redacted)
- Current entity states
- Device information
- Integration settings

**Include diagnostics when filing bug reports.**

---

## Performance Tuning

### Polling Interval

Adjust based on your needs:

| Interval | Use Case |
|----------|----------|
| 10 seconds | Real-time monitoring, critical production |
| 30 seconds | Normal use (default) |
| 60+ seconds | Multiple devices, reduce network load |

Lower intervals mean faster state updates but more network traffic and device load.

### Multiple Devices

When managing many ZowieBox devices:
- Use longer polling intervals (60+ seconds)
- Stagger device additions to spread polling
- Consider using device triggers instead of polling for critical events

---

## Troubleshooting

### Common Issues

**Entity shows "Unknown" or no value:**
- Device may not support that feature
- Check device mode (encoder vs decoder)
- Verify feature is enabled in device web UI

**Services fail silently:**
- Check Home Assistant logs for errors
- Verify device_id is correct
- Ensure device is reachable

**Media playback fails:**
- Verify URL is accessible from the ZowieBox network
- Check if stream format is supported
- Try enabling go2rtc for incompatible formats

### Debug Logging

Enable debug logging for troubleshooting:

```yaml
logger:
  default: info
  logs:
    custom_components.zowietek: debug
```

View logs in **Settings** → **System** → **Logs**.

---

## API Reference

For complete ZowieBox REST API documentation, see [api.md](api.md).
