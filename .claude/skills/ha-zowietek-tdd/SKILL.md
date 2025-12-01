---
name: ha-zowietek-tdd
description: Use when implementing ANY code for the Home Assistant Zowietek integration - enforces strict TDD with RED-GREEN-REFACTOR cycle, requiring tests to fail before implementation and pass after. No exceptions for simple code.
---

# Home Assistant Zowietek TDD

## Overview

**All code for the HA Zowietek integration MUST follow strict Test-Driven Development.**

Write the test first. Watch it fail. Write minimal code to pass. Refactor. No exceptions.

## The Iron Law

```
NO CODE WITHOUT A FAILING TEST FIRST
```

This is non-negotiable. Every function, method, class, and feature starts with a test.

**Write code before test? Delete it. Start over.**

**No exceptions:**
- Not for "simple functions"
- Not for "obvious implementations"
- Not for "just adding a property"
- Not for config flow steps
- Not for entity attributes
- Delete means delete - don't keep as "reference"

## RED-GREEN-REFACTOR Cycle

### RED: Write Failing Test

```python
# tests/test_api.py
async def test_login_success(
    mock_aiohttp_session: MagicMock,
) -> None:
    """Test successful login to ZowieBox."""
    mock_aiohttp_session.post.return_value.__aenter__.return_value.json.return_value = {
        "status": "00000",
        "rsp": "succeed"
    }

    client = ZowietekClient("http://192.168.1.100", "admin", "admin")
    result = await client.login()

    assert result is True
    mock_aiohttp_session.post.assert_called_once()
```

Run the test. **It MUST fail.** If it passes, your test is wrong.

### GREEN: Write Minimal Implementation

```python
# custom_components/zowietek/api.py
async def login(self) -> bool:
    """Authenticate with the ZowieBox device."""
    async with self._session.post(
        f"{self._host}/system?option=setinfo&login_check_flag=1",
        json={"group": "user", "user": self._username, "psw": self._password}
    ) as response:
        data = await response.json()
        return data.get("status") == "00000"
```

Run the test. **It MUST pass now.**

### REFACTOR: Improve Without Breaking

Only refactor when tests pass. Keep them passing throughout.

## Testing Patterns for HA Zowietek

### Config Flow Tests

```python
async def test_config_flow_user_step_success(
    hass: HomeAssistant,
    mock_zowietek_client: MagicMock,
) -> None:
    """Test successful user config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM

    mock_zowietek_client.get_system_info.return_value = {"device_name": "ZowieBox"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ZowieBox"
```

### Entity Tests

```python
async def test_sensor_video_resolution(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_zowietek_client: MagicMock,
) -> None:
    """Test video resolution sensor reports correctly."""
    mock_zowietek_client.get_video_info.return_value = {
        "resolution": "3840x2160",
        "frame_rate": 30,
    }

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.zowiebox_video_resolution")
    assert state.state == "3840x2160"
```

### Fixtures (conftest.py)

```python
@pytest.fixture
def mock_zowietek_client() -> Generator[MagicMock, None, None]:
    """Mock the Zowietek API client."""
    with patch(
        "custom_components.zowietek.ZowietekClient",
        autospec=True,
    ) as mock:
        client = mock.return_value
        client.login.return_value = True
        client.get_system_info.return_value = {
            "device_name": "ZowieBox",
            "serial_number": "ZB123456",
            "firmware_version": "1.0.0",
        }
        yield client


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
        },
        unique_id="zowiebox-123456",
    )
```

## Test Coverage Requirements

**Minimum coverage: 100% for all new code**

Every code path must be tested:
- Happy paths
- Error conditions
- Edge cases
- All config flow branches
- All entity states

Run coverage check:
```bash
pytest tests/ --cov=custom_components.zowietek --cov-report=term-missing --cov-fail-under=100
```

## Common Rationalizations (All Wrong)

| Excuse | Reality |
|--------|---------|
| "It's just a property" | Properties have bugs. Test it. |
| "The API client is already tested" | Integration layer needs tests. Test it. |
| "I'll add tests after" | Tests-after prove nothing. Test first. |
| "Config flow is boilerplate" | Boilerplate has bugs. Test it. |
| "It's obvious how this works" | Obvious code breaks. Test it. |
| "Manual testing is enough" | Manual tests don't catch regressions. Write automated tests. |

## Red Flags - STOP and Start Over

If you catch yourself with ANY of these, delete your code and restart with TDD:

- Code exists without corresponding test
- Test was written after implementation
- "I'll refactor the test later"
- "The existing tests cover this"
- "This is too simple to test"
- Test passes on first run (test is wrong)

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=custom_components.zowietek --cov-report=term-missing

# Run specific test file
pytest tests/test_config_flow.py

# Run single test
pytest tests/test_api.py::test_login_success

# Stop on first failure
pytest tests/ -x
```

## Live Device Testing

For integration tests against real ZowieBox devices, use environment variables.

### Environment Variables

```bash
# Set in .env file (loaded by devcontainer)
ZOWIETEK_URL=http://zow001.signage.sy3.aperim.net
ZOWIETEK_USERNAME=admin
ZOWIETEK_PASSWORD=admin
```

### Accessing Environment Variables

**NEVER read `.env` files directly.** Always use `os.environ`:

```python
import os

# CORRECT
zowietek_url = os.environ.get("ZOWIETEK_URL")
zowietek_username = os.environ.get("ZOWIETEK_USERNAME")

# WRONG - Never do this
# from dotenv import load_dotenv
# load_dotenv()
```

### Live Test Fixtures

```python
import os
import pytest

@pytest.fixture
def live_zowietek_url() -> str | None:
    """Get live Zowietek URL from environment."""
    return os.environ.get("ZOWIETEK_URL")

@pytest.fixture
def live_zowietek_credentials() -> tuple[str, str] | None:
    """Get live Zowietek credentials from environment."""
    username = os.environ.get("ZOWIETEK_USERNAME")
    password = os.environ.get("ZOWIETEK_PASSWORD")
    if username and password:
        return (username, password)
    return None

@pytest.fixture
def requires_live_device(
    live_zowietek_url: str | None,
    live_zowietek_credentials: tuple[str, str] | None,
) -> None:
    """Skip test if live device credentials not available."""
    if not live_zowietek_url or not live_zowietek_credentials:
        pytest.skip("ZOWIETEK_URL and credentials required for live tests")
```

## Mandatory Live Testing Phase

**After GREEN phase, test against real devices.**

Unit tests with mocks prove code logic. Live tests prove real-world behavior.

### Check for Available Devices

```python
import os

zowietek_url = os.environ.get("ZOWIETEK_URL")
zowietek_username = os.environ.get("ZOWIETEK_USERNAME")
zowietek_password = os.environ.get("ZOWIETEK_PASSWORD")
```

**If credentials exist, you MUST test against the device before marking work complete.**

### API Client Testing

```python
import asyncio
import aiohttp
from custom_components.zowietek.api import ZowietekClient

async def test_live():
    async with aiohttp.ClientSession() as session:
        client = ZowietekClient(
            host=os.environ["ZOWIETEK_URL"],
            username=os.environ["ZOWIETEK_USERNAME"],
            password=os.environ["ZOWIETEK_PASSWORD"],
            session=session,
        )
        # Test the methods you changed
        result = await client.async_get_system_time()
        print(f"System time: {result}")

asyncio.run(test_live())
```

### Home Assistant Integration Testing

For changes that affect HA integration behavior:

1. **Start the dev HA instance:**
   ```bash
   # Check if HA is running
   pgrep -f "hass" || hass -c /workspaces/homeassistant-zowietek/config
   ```

2. **Configure integration via UI:**
   - Navigate to Settings → Devices & Services
   - Add Integration → Zowietek
   - Enter device credentials
   - Verify setup completes

3. **Verify entities:**
   - Check entities appear in HA
   - Verify state updates correctly
   - Check logs for errors: `tail -f config/home-assistant.log`

### Why This Matters

Issue #8 taught us: **mocked tests can pass while real behavior is completely broken.**

The original API client had 100% test coverage and all tests passing. But when tested against real devices:
- Login worked
- Every subsequent request failed with "Authentication required"
- The entire API format was wrong

Live testing caught what mocks could not.

## The Bottom Line

**Every line of code starts with a failing test.**

No shortcuts. No exceptions. No rationalizations.

RED -> GREEN -> REFACTOR -> **LIVE TEST**. Always.

See skill: `ha-zowietek-live-testing` for detailed procedures.
