# Home Assistant Zowietek Integration

A from-scratch Home Assistant integration for Zowietek video streaming devices (ZowieBox NDI Encoder/Decoder).

## Project Overview

This is a custom Home Assistant integration that provides control and monitoring for Zowietek ZowieBox devices. It follows Home Assistant 2025 best practices and strict development standards.

## Project Management

### GitHub Project

**ALL work MUST be tracked via GitHub Issues and the Project Board.**

| Item | Value |
|------|-------|
| Repository | troykelly/homeassistant-zowietek |
| Project Board | https://github.com/users/troykelly/projects/4 |

### The Iron Law

```
NO CODE CHANGES WITHOUT A LINKED GITHUB ISSUE
```

This is a **VIOLATION**. Every commit, every PR, every change must reference an issue.

**Before writing ANY code:**
1. Check if an issue exists for this work
2. If not, create one
3. Assign yourself and add `status: in-progress`
4. Create branch: `issue-{N}-{description}`
5. Commit with issue reference: `type(scope): message (#N)`
6. Create PR with `Fixes #N` in body

See skill: `ha-zowietek-github`

## Mandatory Development Rules

### 1. Inclusive Language

**This project uses inclusive language. No exceptions.**

- Default branch is `main`, never `master`
- Use `allowlist`/`denylist`, never `whitelist`/`blacklist`
- Use `primary`/`replica`, never `master`/`slave`
- Use gender-neutral terms (`they`, `them`, `their`)

### 2. No Laziness

**Never take shortcuts. Do the job properly.**

- Never stub out code with `TODO` or `pass` and move on
- Never skip tests because "it's simple"
- Never leave incomplete implementations
- Never use placeholders like `...` in actual code
- If a task requires 10 steps, do all 10 steps
- If you're tired of a task, that's when you focus harder

### 3. Test-Driven Development (TDD)

**Every line of code MUST start with a failing test.**

```
RED → GREEN → REFACTOR
```

- Write test first
- Watch it fail (if it passes immediately, your test is wrong)
- Write minimal code to pass
- Refactor while keeping tests green
- No exceptions for "simple" code

See skill: `ha-zowietek-tdd`

### 4. No `Any` Type

**NEVER use `Any` in type annotations.**

- Use TypedDict for API response structures
- Use dataclasses for internal models
- Use Protocol for interfaces
- Use Generics for containers
- The only exception: `**kwargs: Any` when overriding HA base class methods that require it

See skill: `ha-zowietek-typing`

### 5. Two Failures = Research

**If code fails twice, STOP and research.**

- Don't guess-and-check
- Read official documentation
- Examine working implementations in HA core
- Understand before attempting again

See skill: `ha-zowietek-research`

### 6. Mandatory Live Device Testing

**All code MUST be tested against real devices when available.**

Unit tests with mocks are necessary but NOT sufficient. Before any code is considered complete:

1. **Check for available devices:**
   ```python
   import os
   zowietek_url = os.environ.get("ZOWIETEK_URL")
   zowietek_username = os.environ.get("ZOWIETEK_USERNAME")
   zowietek_password = os.environ.get("ZOWIETEK_PASSWORD")
   ```

2. **If credentials exist, test against the device:**
   - API client changes: Test all affected endpoints
   - Entity changes: Verify state updates from real device
   - Config flow changes: Test actual device discovery/connection

3. **For Home Assistant integration code:**
   - Start/restart the dev HA instance
   - Add/reconfigure the integration via UI
   - Verify entities appear and update correctly
   - Check logs for errors or warnings

**Live testing is NOT optional.** The experience with issue #8 proved that mocked tests can pass while real device behavior is completely different.

See skill: `ha-zowietek-live-testing`

### 7. Never Leak Sensitive Information

**NEVER include real hostnames, URLs, IP addresses, or credentials in:**

- Commit messages
- Pull request descriptions
- Issue comments
- Code comments
- Documentation

**When documenting live testing results, use generic placeholders:**

```markdown
## Live Testing Results

### Device Testing
- **Device 1:** [ZOWIETEK_URL from environment]
  - Connection: OK
  - Authentication: OK

### What to write:
- "Tested against device from ZOWIETEK_URL environment variable"
- "Live device testing passed"
- "All endpoints responded correctly"

### What NOT to write:
- Actual hostnames (e.g., zow001.company.com)
- IP addresses (e.g., 192.168.1.100)
- Internal domain names
- Any identifying infrastructure information
```

**This is a SECURITY requirement.** Leaking infrastructure details can expose:
- Internal network topology
- Device locations
- Potential attack vectors

## Project Structure

```
custom_components/zowietek/
├── __init__.py           # Integration setup, async_setup_entry
├── manifest.json         # Integration metadata
├── config_flow.py        # UI configuration flow
├── const.py              # Constants, types, TypedDicts
├── coordinator.py        # DataUpdateCoordinator
├── entity.py             # Base ZowietekEntity class
├── api.py                # ZowieBox API client wrapper
├── models.py             # Dataclasses for internal models
│
│   # Entity Platforms
├── sensor.py             # SensorEntity - device status, stream info
├── binary_sensor.py      # BinarySensorEntity - streaming state
├── switch.py             # SwitchEntity - enable/disable streams
├── button.py             # ButtonEntity - actions (reboot, etc.)
├── select.py             # SelectEntity - video mode selection
│
│   # Supporting
├── services.py           # Custom services
├── exceptions.py         # Custom exceptions
├── diagnostics.py        # Diagnostic download
├── strings.json          # English translations
└── translations/
    └── en.json

tests/
├── conftest.py           # Pytest fixtures
├── test_init.py          # Setup/unload tests
├── test_config_flow.py   # Config flow tests
├── test_coordinator.py   # Coordinator tests
├── test_api.py           # API client tests
├── test_sensor.py        # Sensor tests
└── ...                   # Additional test files
```

## Key Technologies

- **Python 3.13+** - Type hints with modern syntax (`X | None`, not `Optional[X]`)
- **Home Assistant 2025.x** - Latest patterns and APIs
- **pytest + pytest-homeassistant-custom-component** - Testing framework
- **mypy strict** - Type checking
- **aiohttp** - Async HTTP client
- **ZowieBox REST API** - Device communication

## ZowieBox API Reference

### Authentication

The ZowieBox uses session-based authentication with credentials sent per-request:

```python
# Login request
POST /system?option=setinfo&login_check_flag=1
Content-Type: application/json
{"group":"user","user":"admin","psw":"admin"}

# Response
{"status":"00000","rsp":"succeed"}
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/system?option=getinfo` | POST | System information (firmware, model, etc.) |
| `/system?option=setinfo` | POST | Update system settings |
| `/video?option=getinfo` | POST | Video input/output settings |
| `/video?option=setinfo` | POST | Update video settings |
| `/audio?option=getinfo` | POST | Audio settings |
| `/audio?option=setinfo` | POST | Update audio settings |
| `/network?option=getinfo` | POST | Network configuration |
| `/network?option=setinfo` | POST | Update network settings |
| `/stream?option=getinfo` | POST | NDI/RTMP/SRT stream settings |
| `/stream?option=setinfo` | POST | Update stream settings |
| `/streamplay?option=getinfo` | POST | Decoder playback settings |
| `/streamplay?option=setinfo` | POST | Update playback settings |
| `/third_api?option=getinfo` | POST | Third-party API configuration |

### Status Codes

| Code | Meaning |
|------|---------|
| `00000` | Success |
| `00003` | Invalid parameters (check `group` field) |
| `80003` | Not logged in / authentication required |

### Request Format

All requests require a JSON body with at minimum a `group` field:

```json
{"group": "all"}
```

For authenticated requests, include credentials:

```json
{"group": "all", "user": "admin", "psw": "admin"}
```

## Environment Variables

### Live Device Testing

For testing against live ZowieBox devices, set these environment variables in `.env`:

```bash
# Primary test device
ZOWIETEK_URL=http://zow001.example.com
ZOWIETEK_USERNAME=admin
ZOWIETEK_PASSWORD=admin

# Secondary test device (optional)
ZOWIETEK_URL_2=http://zow002.example.com
ZOWIETEK_USERNAME_2=admin
ZOWIETEK_PASSWORD_2=admin
```

The devcontainer automatically loads `.env` into the container environment.

### Home Assistant Devcontainer Testing

```bash
HOMEASSISTANT_URL=http://localhost:8123
HOMEASSISTANT_TOKEN=your-long-lived-access-token
```

### Accessing Environment Variables

**NEVER read `.env` files directly in code.** Always use `os.environ`:

```python
import os

# CORRECT - Read from environment
zowietek_url = os.environ.get("ZOWIETEK_URL")
zowietek_username = os.environ.get("ZOWIETEK_USERNAME")
zowietek_password = os.environ.get("ZOWIETEK_PASSWORD")

# WRONG - Never do this
# from dotenv import load_dotenv
# load_dotenv()
```

## Development Commands

```bash
# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=custom_components.zowietek --cov-report=term-missing --cov-fail-under=100

# Run specific test
pytest tests/test_api.py::test_login -v

# Type checking
mypy custom_components/zowietek/

# Linting
ruff check custom_components/zowietek/
ruff format custom_components/zowietek/
```

## Testing Patterns

### Required Fixtures (conftest.py)

```python
@pytest.fixture
def mock_zowietek_client() -> Generator[MagicMock, None, None]:
    """Mock ZowieBox API client."""
    with patch("custom_components.zowietek.ZowietekClient", autospec=True) as mock:
        yield mock.return_value

@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_USERNAME: "admin", CONF_PASSWORD: "admin"},
        unique_id="zowiebox-abc123",
    )
```

### Test Coverage Requirements

- 100% coverage for all code
- All config flow paths (success, errors, abort)
- All entity states
- All service methods
- Error handling paths

## Code Style

- Use `from __future__ import annotations`
- Modern union syntax: `str | None` not `Optional[str]`
- Explicit return types on all functions
- Type all class attributes in `__init__`
- Use `_attr_*` pattern for entity attributes
- Never do I/O in properties

## Skills Reference

This project uses specialized skills for consistent, high-quality development. Skills are located in `.claude/skills/`.

### Skill Usage Matrix

| Situation | Required Skill | When to Use |
|-----------|----------------|-------------|
| Starting work session | `ha-zowietek-issue-selector` | Select next issue from project board |
| Bug needs investigation | `ha-zowietek-bug-triage` | Reproduce, gather evidence, update issue |
| Implementing fix/feature | `ha-zowietek-issue-executor` | TDD implementation linked to issue |
| GitHub operations | `ha-zowietek-github` | Issue/PR management, commit format |
| Writing ANY code | `ha-zowietek-tdd` | Automatic with issue-executor |
| Type annotations | `ha-zowietek-typing` | Automatic with issue-executor |
| Failed twice | `ha-zowietek-research` | Stop and research before continuing |
| HA patterns | `ha-zowietek-integration` | Reference for HA best practices |
| Before marking complete | `ha-zowietek-live-testing` | Validate against real devices and HA |

## Device Capabilities

The ZowieBox supports various operating modes:

### Encoder Mode
- HDMI input to NDI|HX3 output
- HDMI input to RTMP/RTSP/SRT stream
- Up to 4K30 encoding
- 4K60 loop-through

### Decoder Mode
- NDI|HX3 input to HDMI output
- RTSP/SRT/RTMP input to HDMI output
- UVC input to HDMI output
- Up to 4K30 decoding

### Settings Categories
- Video: Input source, resolution, frame rate, encoder settings
- Audio: Input source, volume, codec settings
- Stream: NDI name, RTMP URL, SRT settings
- Network: IP configuration, WiFi settings
- System: Device name, firmware, time settings

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Config Flow Docs](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
- [Zowietek Product Page](https://zowietek.com/product/4k-video-streaming-encoder-decoder/)
- [Bitfocus Companion Module for Zowietek](https://github.com/bitfocus/companion-module-zowietek-api) - Excellent reference for ZowieBox API endpoints, actions, and capabilities
