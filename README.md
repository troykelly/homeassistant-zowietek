# Zowietek for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/troykelly/homeassistant-zowietek.svg)](https://github.com/troykelly/homeassistant-zowietek/releases)
[![License](https://img.shields.io/github/license/troykelly/homeassistant-zowietek.svg)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/troykelly/homeassistant-zowietek/test.yml?label=tests)](https://github.com/troykelly/homeassistant-zowietek/actions)

Control your ZowieBox video encoder/decoder from Home Assistant.

## What Can It Do?

- **Monitor** your video streams, device health, and signal status
- **Control** NDI, RTMP, and SRT streaming with a single tap
- **Play** streams on your decoder from Home Assistant
- **Automate** based on video signal detection or streaming events

## Quick Install

### Option 1: HACS (Recommended)

1. Open **HACS** → three-dot menu → **Custom repositories**
2. Add `https://github.com/troykelly/homeassistant-zowietek` as an **Integration**
3. Search for **Zowietek** and install
4. Restart Home Assistant

### Option 2: Manual

1. Download the [latest release](https://github.com/troykelly/homeassistant-zowietek/releases)
2. Extract `custom_components/zowietek` to your `config/custom_components/` folder
3. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Zowietek**
3. Select your device (auto-discovered) or enter the IP manually
4. Enter credentials (default: `admin` / `admin`)

That's it! Your ZowieBox entities will appear automatically.

---

## Supported Devices

| Device | Features |
|--------|----------|
| **ZowieBox** | 4K HDMI NDI Encoder/Decoder |

**Capabilities:** NDI|HX3, 4K30 encoding/decoding, 4K60 passthrough, RTSP/SRT/RTMP streaming, UVC-to-NDI conversion

---

## Entities Created

Each ZowieBox device creates these entities:

| Type | Entities |
|------|----------|
| **Sensors** | Resolution, frame rate, bitrate, encoder type, NDI name, firmware, uptime, CPU temp/usage |
| **Binary Sensors** | Streaming active, video input detected, NDI/RTMP/SRT enabled |
| **Switches** | NDI stream, RTMP stream, SRT stream |
| **Selects** | Encoder type, output format |
| **Numbers** | Audio volume, stream bitrate |
| **Buttons** | Reboot, refresh |
| **Media Player** | Decoder playback control (sources, play/stop, standby) |

---

## Example Automations

### Notify when video signal is lost

```yaml
automation:
  - alias: "Video input lost alert"
    trigger:
      - platform: device
        domain: zowietek
        device_id: !input zowiebox_device
        type: video_input_lost
    action:
      - service: notify.mobile_app
        data:
          message: "Video signal lost on ZowieBox!"
```

### Start streaming when motion detected

```yaml
automation:
  - alias: "Stream on motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_motion
        to: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.zowiebox_ndi_stream
```

---

## Services

Configure streaming programmatically:

| Service | Purpose |
|---------|---------|
| `zowietek.set_ndi_settings` | Set NDI stream name and group |
| `zowietek.set_rtmp_url` | Configure RTMP destination URL and key |
| `zowietek.set_srt_settings` | Configure SRT port, latency, and passphrase |

See [Advanced Configuration](docs/ADVANCED.md) for full service documentation.

---

## Troubleshooting

### Device not discovered?

ZowieBox uses UDP multicast discovery (`224.170.1.242:21007`). If auto-discovery fails:
- Use manual configuration with the device IP address
- Check that your network allows multicast traffic
- Ensure the device is on the same network/VLAN

### Device shows unavailable?

1. Verify the device is reachable: open `http://<device-ip>/` in a browser
2. Check credentials (default: `admin` / `admin`)
3. Try the **Refresh** button entity
4. Download **Diagnostics** from the device page for troubleshooting

---

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docs/QUICK_START.md) | Step-by-step setup for beginners |
| [Advanced Configuration](docs/ADVANCED.md) | Services, triggers, go2rtc, and more |
| [API Reference](docs/api.md) | ZowieBox REST API documentation |
| [Contributing](CONTRIBUTING.md) | Development setup and guidelines |
| [Changelog](CHANGELOG.md) | Version history |

---

## FAQ

**Q: Does this work with ZowieCam or ZowiePTZ?**
A: Currently optimized for ZowieBox. Other devices may work with limited functionality.

**Q: Can I use multiple devices?**
A: Yes, add each device separately through the integration.

**Q: Why doesn't SSDP/mDNS discovery work?**
A: ZowieBox only supports its proprietary UDP discovery protocol.

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.

```bash
git clone https://github.com/troykelly/homeassistant-zowietek.git
cd homeassistant-zowietek
pip install -r requirements_test.txt
pytest tests/
```

---

## License

Apache License 2.0 - see [LICENSE](LICENSE)

---

## Disclaimer

This integration is not affiliated with, endorsed by, or connected to Zowietek. "Zowietek" and "ZowieBox" are trademarks of their respective owners.

## Acknowledgments

- [Bitfocus Companion Module for Zowietek](https://github.com/bitfocus/companion-module-zowietek-api) - API reference
