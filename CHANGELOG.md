# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2024-12-03

### Fixed
- go2rtc load order ensuring proper initialization before use (#64, #65)
- go2rtc error handling improvements for better reliability
- Removed dead HTTP stream type code for 100% test coverage

### Changed
- Refactored media_player with go2rtc helper methods for cleaner code
- Improved error messages for go2rtc-related failures

## [0.2.0] - 2024-12-03

### Added
- go2rtc integration for HLS/DASH stream conversion
- Camera entity playback support via go2rtc
- Configuration option to enable/disable go2rtc conversion
- Quick Start guide for beginners (`docs/QUICK_START.md`)
- Advanced configuration documentation (`docs/ADVANCED.md`)

### Changed
- Refactored README for better accessibility (simple content above the fold)
- Improved documentation structure with progressive disclosure
- Enhanced CHANGELOG with categorized sections

### Fixed
- HTTP URLs now properly convert through go2rtc when needed

## [0.1.0] - 2024-12-01

Initial release of the Zowietek integration for Home Assistant.

### Added

**Device Support**
- ZowieBox 4K HDMI NDI Encoder/Decoder
- Automatic device discovery via UDP multicast
- Manual device configuration by IP address

**Entities**
- Sensors: resolution, frame rate, bitrate, encoder type, NDI name, firmware, hardware version, serial number, uptime, CPU temperature, CPU usage
- Binary sensors: streaming status, video input detection, NDI/RTMP/SRT enabled states
- Switches: NDI, RTMP, and SRT stream control
- Selects: encoder type, output format
- Numbers: audio volume, stream bitrate
- Buttons: reboot, refresh
- Media player: decoder playback with source selection and stream URL support

**Services**
- `zowietek.set_ndi_settings` - Configure NDI stream name and group
- `zowietek.set_rtmp_url` - Set RTMP destination URL and stream key
- `zowietek.set_srt_settings` - Configure SRT port, latency, and passphrase

**Device Triggers**
- `stream_started` - Triggered when any stream output activates
- `stream_stopped` - Triggered when all stream outputs stop
- `video_input_detected` - Triggered when HDMI video signal is detected
- `video_input_lost` - Triggered when HDMI video signal is lost

**Configuration**
- Config flow for UI-based device setup
- Options flow for update interval configuration
- Reauthentication flow for credential updates
- Reconfiguration flow for host/credential changes

**Other**
- Diagnostics download for troubleshooting
- Full translation support (English)

### Technical

- Python 3.13+ support
- Home Assistant 2025.11.3+ required
- 100% test coverage
- Strict type checking with mypy
- TypedDict definitions for all API responses

[Unreleased]: https://github.com/troykelly/homeassistant-zowietek/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/troykelly/homeassistant-zowietek/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/troykelly/homeassistant-zowietek/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/troykelly/homeassistant-zowietek/releases/tag/v0.1.0
