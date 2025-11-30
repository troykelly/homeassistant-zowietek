# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffolding
- Development environment setup (devcontainer)
- GitHub workflows for CI/CD
- Issue templates for bug reports, feature requests, and support

## [0.1.0] - TBD

### Added
- Initial release of Home Assistant Zowietek integration
- Config flow for device setup
- Support for ZowieBox 4K HDMI NDI Encoder/Decoder
- Sensor entities for device status and stream information
- Binary sensor entities for streaming state
- Switch entities for stream control (NDI, RTMP, SRT, RTSP)
- Select entities for video mode and input source
- Button entities for device actions (reboot, etc.)
- Custom services for advanced control
- Diagnostics download for troubleshooting

### Technical
- Python 3.13+ support (Home Assistant 2025.x)
- 100% test coverage requirement
- Strict type checking with mypy
- TypedDict definitions for API responses

[Unreleased]: https://github.com/troykelly/homeassistant-zowietek/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/troykelly/homeassistant-zowietek/releases/tag/v0.1.0
