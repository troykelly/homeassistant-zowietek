# Zowietek Integration for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/troykelly/homeassistant-zowietek.svg)](https://github.com/troykelly/homeassistant-zowietek/releases)
[![License](https://img.shields.io/github/license/troykelly/homeassistant-zowietek.svg)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/troykelly/homeassistant-zowietek/test.yml?label=tests)](https://github.com/troykelly/homeassistant-zowietek/actions)

A Home Assistant custom integration for **Zowietek** video streaming devices, including the ZowieBox 4K HDMI NDI Video Encoder/Decoder.

## Overview

This integration enables complete control and monitoring of ZowieBox devices from Home Assistant. You can:

- Monitor video input status, encoding settings, and device health
- Control NDI, RTMP, and SRT streaming outputs
- Play and control stream sources in decoder mode
- Automate based on video signal detection and streaming events
- Configure encoding and output settings

## Supported Devices

| Device | Features |
|--------|----------|
| **ZowieBox** | 4K HDMI NDI Video Encoder/Decoder |

### ZowieBox Capabilities

- **NDI|HX3** encoding/decoding
- Up to **4K30** hardware encoding/decoding
- **4K60/1080p120Hz** loop-through
- **RTSP, SRT, RTMP** streaming protocols
- **UVC** to NDI/HDMI conversion
- Automatic device discovery via UDP multicast

## Installation

### HACS (Recommended)

1. Open **HACS** in your Home Assistant instance
2. Click the three dots menu in the top right corner
3. Select **Custom repositories**
4. Add this repository URL: `https://github.com/troykelly/homeassistant-zowietek`
5. Select **Integration** as the category
6. Click **Add**
7. Search for **Zowietek** and click **Download**
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/troykelly/homeassistant-zowietek/releases)
2. Extract the `custom_components/zowietek` folder to your Home Assistant `config/custom_components` directory
3. Restart Home Assistant

## Configuration

### Adding a Device

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for **Zowietek**
4. Either:
   - Select a discovered device from the list, or
   - Choose **Enter manually** to configure by IP/hostname
5. Enter credentials (default: `admin` / `admin`)

### Configuration Options

After adding a device, you can configure:

| Option | Description | Default |
|--------|-------------|---------|
| Update interval | How often to poll the device (10-300 seconds) | 30 seconds |

Access options via **Settings** > **Devices & Services** > **Zowietek** > **Configure**

### Reconfiguration

To update device credentials or host address:
1. Go to the device's integration page
2. Click **Reconfigure**
3. Enter the updated settings

## Entities

The integration creates the following entities for each device:

### Sensors

| Entity | Description |
|--------|-------------|
| Video resolution | Current encoding resolution (e.g., "1920x1080") |
| Frame rate | Current encoding frame rate (fps) |
| Stream bitrate | Current encoding bitrate (bps) |
| Encoder type | Active video codec (H.264/H.265) |
| NDI name | Configured NDI stream name |
| Output format | HDMI output format |
| Firmware version | Device firmware version |
| Hardware version | Device hardware version |
| Serial number | Device serial number |
| Uptime | Device uptime |
| CPU temperature | Current CPU temperature (°C) |
| CPU usage | Current CPU utilization (%) |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| Streaming | On when any stream output is active |
| Video input | On when HDMI input signal is detected |
| NDI enabled | On when NDI output is enabled |
| RTMP enabled | On when RTMP output is enabled |
| SRT enabled | On when SRT output is enabled |

### Switches

| Entity | Description |
|--------|-------------|
| NDI stream | Enable/disable NDI|HX output |
| RTMP stream | Enable/disable RTMP streaming |
| SRT stream | Enable/disable SRT streaming |

### Select

| Entity | Options |
|--------|---------|
| Encoder type | H.264, H.265 (device-dependent) |
| Output format | 720p50, 720p60, 1080p50, 1080p60, 2160p30, etc. |

### Number

| Entity | Range | Description |
|--------|-------|-------------|
| Audio volume | 0-100% | Audio input volume level |
| Stream bitrate | 1-50 Mbps | Encoding bitrate |

### Buttons

| Entity | Action |
|--------|--------|
| Reboot | Restart the device |
| Refresh | Force a data refresh from the device |

### Media Player (Decoder Mode)

The **Decoder** media player entity provides playback control:

| Feature | Description |
|---------|-------------|
| **State** | Playing, Idle, Standby |
| **Source selection** | Switch between configured stream sources |
| **NDI sources** | Select from discovered NDI sources on the network |
| **Play media** | Play arbitrary URLs (RTSP, RTMP, SRT, HTTP) |
| **Stop** | Stop current playback |
| **Turn off** | Put device into standby mode |
| **Turn on** | Wake device from standby |

**Media types supported:**
- RTSP streams (`rtsp://...`)
- RTMP streams (`rtmp://...`)
- SRT streams (`srt://...`)
- HTTP/HTTPS streams (`http://...`, `https://...`)

## Services

The integration provides custom services for advanced configuration:

### `zowietek.set_ndi_settings`

Configure NDI stream name and group.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `device_id` | Yes | Target device |
| `name` | Yes | NDI stream name |
| `group` | No | NDI group name |

**Example:**
```yaml
service: zowietek.set_ndi_settings
data:
  device_id: "abc123..."
  name: "Studio-Camera-1"
  group: "Production"
```

### `zowietek.set_rtmp_url`

Configure RTMP streaming destination.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `device_id` | Yes | Target device |
| `url` | Yes | RTMP server URL |
| `key` | No | Stream key |

**Example:**
```yaml
service: zowietek.set_rtmp_url
data:
  device_id: "abc123..."
  url: "rtmp://live.example.com/live"
  key: "stream_key_123"
```

### `zowietek.set_srt_settings`

Configure SRT streaming settings.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `device_id` | Yes | Target device |
| `port` | Yes | SRT port (1-65535) |
| `latency` | No | Latency in ms (20-8000) |
| `passphrase` | No | Encryption passphrase |

**Example:**
```yaml
service: zowietek.set_srt_settings
data:
  device_id: "abc123..."
  port: 9000
  latency: 120
  passphrase: "secure_phrase"
```

## Device Triggers

Use these triggers in automations:

| Trigger | Description |
|---------|-------------|
| `stream_started` | Any stream output (NDI/RTMP/SRT) started |
| `stream_stopped` | All stream outputs stopped |
| `video_input_detected` | HDMI video signal detected |
| `video_input_lost` | HDMI video signal lost |

**Example Automation:**
```yaml
automation:
  - alias: "Notify on video input lost"
    trigger:
      - platform: device
        domain: zowietek
        device_id: "abc123..."
        type: video_input_lost
    action:
      - service: notify.mobile_app
        data:
          message: "Video input lost on ZowieBox!"
```

## Troubleshooting

### Device Not Discovered

ZowieBox devices use a proprietary UDP multicast discovery protocol:
- **Multicast address:** `224.170.1.242`
- **Port:** `21007`

If automatic discovery fails:
1. Ensure your network allows UDP multicast
2. Use manual configuration with the device IP address
3. Check that the device is on the same network/VLAN

### Connection Issues

1. **Verify device accessibility:** Open `http://<device-ip>/` in a browser
2. **Check credentials:** Default is `admin` / `admin`
3. **Review logs:** Check Home Assistant logs for error details
4. **Firewall:** Ensure port 80 (HTTP) is accessible

### Entity Shows "Unavailable"

- Device may be offline or unreachable
- Network connectivity issue
- Device may be rebooting
- Try the **Refresh** button entity

### Diagnostics

Download device diagnostics for troubleshooting:
1. Go to **Settings** > **Devices & Services** > **Zowietek**
2. Click on your device
3. Click **Download diagnostics**

This provides sanitized device information useful for bug reports.

## FAQ

**Q: Does this work with ZowieCam or ZowiePTZ?**
A: Currently optimized for ZowieBox. Other devices may work with limited functionality.

**Q: Can I control PTZ cameras through the ZowieBox?**
A: PTZ control is not yet implemented but may be added in future versions.

**Q: Why doesn't SSDP/mDNS discovery work?**
A: ZowieBox devices only support their proprietary UDP discovery protocol, not standard protocols like SSDP or mDNS.

**Q: Can I use this for multiple devices?**
A: Yes, add each device separately through the integration configuration.

**Q: How do I update the NDI name?**
A: Use the `zowietek.set_ndi_settings` service or the device's web interface.

## API Reference

For detailed API documentation, see [docs/api.md](docs/api.md).

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

### Quick Start for Contributors

```bash
git clone https://github.com/troykelly/homeassistant-zowietek.git
cd homeassistant-zowietek
python -m venv venv
source venv/bin/activate
pip install -r requirements_test.txt

# Run tests
pytest tests/

# Type checking
mypy custom_components/zowietek/

# Linting
ruff check custom_components/zowietek/
```

## Acknowledgments

- **[Bitfocus Companion Module for Zowietek](https://github.com/bitfocus/companion-module-zowietek-api)** - Invaluable API reference for ZowieBox devices

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with, endorsed by, or connected to Zowietek in any way. "Zowietek" and "ZowieBox" are trademarks of their respective owners.
