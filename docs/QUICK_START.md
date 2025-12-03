# Quick Start Guide

Get your ZowieBox working with Home Assistant in 5 minutes.

## Before You Start

You'll need:
- A ZowieBox device on your network
- Home Assistant 2025.11.3 or newer
- Device credentials (default: `admin` / `admin`)

## Step 1: Install the Integration

### Using HACS (Recommended)

1. Open Home Assistant
2. Go to **HACS** in the sidebar
3. Click the three-dot menu (top right) → **Custom repositories**
4. Enter: `https://github.com/troykelly/homeassistant-zowietek`
5. Select **Integration** as the category
6. Click **Add**
7. Close the dialog, then search for **Zowietek**
8. Click **Download**
9. Restart Home Assistant

### Manual Installation

1. Download the [latest release](https://github.com/troykelly/homeassistant-zowietek/releases)
2. Unzip and copy the `custom_components/zowietek` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Step 2: Add Your Device

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration** (bottom right)
3. Search for **Zowietek**
4. Choose your device:
   - **Auto-discovered**: Select it from the list
   - **Manual**: Choose "Enter manually" and type the IP address
5. Enter your credentials:
   - Username: `admin` (default)
   - Password: `admin` (default)
6. Click **Submit**

Your device is now connected!

## Step 3: Find Your Entities

After setup, navigate to:
- **Settings** → **Devices & Services** → **Zowietek**
- Click on your device to see all entities

You'll find:

| Entity Type | What It Does |
|-------------|--------------|
| **Sensors** | Show resolution, frame rate, bitrate, uptime, etc. |
| **Binary Sensors** | Indicate if streaming is active, video input detected |
| **Switches** | Turn NDI/RTMP/SRT streams on or off |
| **Media Player** | Control decoder playback |
| **Buttons** | Reboot device, force refresh |

## Step 4: Create Your First Automation

Here's a simple automation that notifies you when the video input is lost:

1. Go to **Settings** → **Automations & Scenes**
2. Click **+ Create Automation**
3. Choose **Create new automation**
4. Click **Add Trigger** → **Device**
5. Select your ZowieBox device
6. Choose **Video input lost**
7. Click **Add Action** → **Call service**
8. Choose your notification service
9. Enter your message
10. Save!

Example YAML:

```yaml
alias: ZowieBox Video Lost Alert
trigger:
  - platform: device
    domain: zowietek
    device_id: YOUR_DEVICE_ID
    type: video_input_lost
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "ZowieBox Alert"
      message: "Video signal lost!"
```

## Step 5: Control Streaming

### Using the UI

- Find the **NDI Stream**, **RTMP Stream**, or **SRT Stream** switch
- Toggle it on/off to start/stop streaming

### Using Automations

```yaml
# Start NDI when motion is detected
alias: Stream on Motion
trigger:
  - platform: state
    entity_id: binary_sensor.front_door_motion
    to: "on"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.zowiebox_ndi_stream
```

## Step 6: Play Streams (Decoder Mode)

If your ZowieBox is in decoder mode, use the Media Player entity:

### Switch Sources

1. Find the **Decoder** media player entity
2. Open it and select a source from the dropdown
3. Sources include configured streams and discovered NDI sources

### Play Custom URLs

Use the `media_player.play_media` service:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.zowiebox_decoder
data:
  media_content_type: url
  media_content_id: "rtsp://your-stream-url"
```

Supported URL types:
- `rtsp://` - RTSP streams
- `rtmp://` - RTMP streams
- `srt://` - SRT streams
- `http://` / `https://` - HTTP streams

## Common Issues

### "Device not discovered"

The ZowieBox uses UDP multicast for discovery. Try:
1. Use manual IP entry instead
2. Check that multicast is allowed on your network
3. Verify the device and Home Assistant are on the same VLAN

### "Authentication failed"

1. Verify credentials work in the device's web interface
2. Try the default credentials: `admin` / `admin`
3. Reset the device if you've forgotten the password

### "Entity shows Unavailable"

1. Check if the device is powered on
2. Verify network connectivity
3. Try the **Refresh** button entity
4. Check Home Assistant logs for errors

## Next Steps

- [Advanced Configuration](ADVANCED.md) - Services, triggers, go2rtc integration
- [API Reference](api.md) - Full ZowieBox API documentation
- [Contributing](../CONTRIBUTING.md) - Help improve this integration

## Need Help?

- Check [existing issues](https://github.com/troykelly/homeassistant-zowietek/issues)
- Open a [new issue](https://github.com/troykelly/homeassistant-zowietek/issues/new/choose)
- Download **Diagnostics** from your device page for bug reports
