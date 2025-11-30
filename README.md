# Home Assistant Zowietek Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/troykelly/homeassistant-zowietek.svg)](https://github.com/troykelly/homeassistant-zowietek/releases)
[![License](https://img.shields.io/github/license/troykelly/homeassistant-zowietek.svg)](LICENSE)

A Home Assistant custom integration for **Zowietek** video streaming devices, including the ZowieBox 4K HDMI NDI Video Encoder/Decoder.

## Status

🚧 **Pre-Alpha / In Development** 🚧

This integration is currently under active development. Not all features are implemented yet.

## Supported Devices

- **ZowieBox** - 4K HDMI NDI Video Encoder/Decoder
  - NDI|HX3 encoding/decoding
  - Up to 4K30 hardware encoding/decoding
  - 4K60/1080p120Hz loop-through
  - RTSP, SRT, RTMP streaming
  - UVC to NDI/HDMI conversion

## Planned Features

- **Device Discovery** - Automatically discover ZowieBox devices on your network
- **Status Monitoring** - Real-time status of encoding/decoding state
- **Stream Control** - Start/stop streaming
- **Video Input/Output Configuration** - Resolution, format settings
- **NDI Settings** - NDI stream configuration
- **Network Settings** - Network configuration monitoring
- **Diagnostics** - Device health and status information

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL: `https://github.com/troykelly/homeassistant-zowietek`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Zowietek" and install

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/troykelly/homeassistant-zowietek/releases)
2. Extract the `custom_components/zowietek` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Zowietek"
4. Enter your ZowieBox device details:
   - Host/IP address
   - Username (default: `admin`)
   - Password (default: `admin`)

## Development

See [CLAUDE.md](CLAUDE.md) for development guidelines and project structure.

### Prerequisites

- Docker (for devcontainer)
- VS Code with Dev Containers extension
- Or: Python 3.13+, Home Assistant development environment

### Quick Start

1. Clone the repository
2. Open in VS Code
3. When prompted, "Reopen in Container"
4. Run `ha` to start Home Assistant
5. Run `pytest` to run tests

## ZowieBox API Reference

The ZowieBox uses a JSON-based HTTP API:

### Authentication

```bash
# Login
POST /system?option=setinfo&login_check_flag=1
Content-Type: application/json
{"group":"user","user":"admin","psw":"admin"}

# Response
{"status":"00000","rsp":"succeed"}
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/system?option=getinfo` | POST | System information |
| `/video?option=getinfo` | POST | Video input/output settings |
| `/audio?option=getinfo` | POST | Audio settings |
| `/network?option=getinfo` | POST | Network configuration |
| `/stream?option=getinfo` | POST | Stream settings |
| `/streamplay?option=getinfo` | POST | Stream playback settings |

### Status Codes

| Code | Meaning |
|------|---------|
| `00000` | Success |
| `00003` | Invalid parameters |
| `80003` | Not logged in |

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with, endorsed by, or connected to Zowietek in any way. "Zowietek" and "ZowieBox" are trademarks of their respective owners.
