---
name: ha-zowietek-live-testing
description: Use when ANY code implementation is complete - MANDATORY validation against real ZowieBox devices and dev Home Assistant instance. Unit tests alone are insufficient. This skill must be invoked before marking any work as complete.
---

# Home Assistant Zowietek Live Testing

## Overview

**Unit tests with mocks are NOT sufficient. Live testing is MANDATORY.**

Issue #8 proved this conclusively: the original API client had 100% test coverage with all tests passing, but was completely broken against real devices. The API format assumptions were entirely wrong.

This skill defines mandatory procedures for validating code against:
1. Real ZowieBox devices
2. Dev Home Assistant instance

## The Iron Law

```
NO CODE IS COMPLETE WITHOUT LIVE TESTING
```

If device credentials are available, you MUST test against real devices.
If changes affect HA behavior, you MUST test in the dev HA instance.

**Skipping live testing is a VIOLATION.**

## When to Use This Skill

- After TDD cycle completes (RED -> GREEN -> REFACTOR)
- Before creating a PR
- Before marking any issue as complete
- When debugging behavior that differs between tests and reality

## Check for Available Devices

**ALWAYS check first. NEVER assume credentials aren't available.**

```python
import os

# Primary device
zowietek_url = os.environ.get("ZOWIETEK_URL")
zowietek_username = os.environ.get("ZOWIETEK_USERNAME")
zowietek_password = os.environ.get("ZOWIETEK_PASSWORD")

# Secondary device (if available)
zowietek_url_2 = os.environ.get("ZOWIETEK_URL_2")
zowietek_username_2 = os.environ.get("ZOWIETEK_USERNAME_2")
zowietek_password_2 = os.environ.get("ZOWIETEK_PASSWORD_2")

print(f"Primary device: {zowietek_url}")
print(f"Secondary device: {zowietek_url_2}")
```

**NEVER read `.env` files directly. Always use `os.environ`.**

## Part 1: ZowieBox Device Testing

### When Required

Test against real ZowieBox devices when changing:
- `api.py` - Any API client code
- `coordinator.py` - Data fetching logic
- `config_flow.py` - Connection/authentication logic
- Any code that makes HTTP requests to the device

### Test Procedure

```python
import asyncio
import aiohttp
import os
from custom_components.zowietek.api import ZowietekClient

async def test_live_device(url: str, username: str, password: str) -> None:
    """Test all API methods against a live device."""
    print(f"\n{'='*60}")
    print(f"Testing device: {url}")
    print(f"{'='*60}\n")

    async with aiohttp.ClientSession() as session:
        client = ZowietekClient(
            host=url,
            username=username,
            password=password,
            session=session,
        )

        # Test connection
        print("Testing connection...")
        try:
            connected = await client.async_test_connection()
            print(f"  Connection: {'OK' if connected else 'FAILED'}")
        except Exception as e:
            print(f"  Connection: FAILED - {e}")
            return

        # Test authentication
        print("Testing authentication...")
        try:
            valid = await client.async_validate_credentials()
            print(f"  Authentication: {'OK' if valid else 'FAILED'}")
        except Exception as e:
            print(f"  Authentication: FAILED - {e}")

        # Test each endpoint
        endpoints = [
            ("System Time", client.async_get_system_time),
            ("Video Info", client.async_get_video_info),
            ("Input Signal", client.async_get_input_signal),
            ("Output Info", client.async_get_output_info),
            ("Stream Publish", client.async_get_stream_publish_info),
            ("NDI Config", client.async_get_ndi_config),
        ]

        for name, method in endpoints:
            print(f"Testing {name}...")
            try:
                result = await method()
                print(f"  {name}: OK")
                print(f"    Response: {result}")
            except Exception as e:
                print(f"  {name}: FAILED - {e}")

async def main() -> None:
    # Test primary device
    url = os.environ.get("ZOWIETEK_URL")
    username = os.environ.get("ZOWIETEK_USERNAME")
    password = os.environ.get("ZOWIETEK_PASSWORD")

    if url and username and password:
        await test_live_device(url, username, password)
    else:
        print("Primary device credentials not available")

    # Test secondary device
    url_2 = os.environ.get("ZOWIETEK_URL_2")
    username_2 = os.environ.get("ZOWIETEK_USERNAME_2")
    password_2 = os.environ.get("ZOWIETEK_PASSWORD_2")

    if url_2 and username_2 and password_2:
        await test_live_device(url_2, username_2, password_2)

if __name__ == "__main__":
    asyncio.run(main())
```

### What to Verify

| Area | Check |
|------|-------|
| **Connection** | Device responds to requests |
| **Authentication** | Credentials are accepted |
| **Data Retrieval** | All GET endpoints return valid data |
| **Data Format** | Response structure matches TypedDict definitions |
| **Write Operations** | SET operations work (test carefully!) |
| **Error Handling** | Invalid requests return expected errors |

### Testing Write Operations

**CAUTION:** Write operations can affect device configuration.

```python
# Test write operation with safe, reversible change
async def test_write_operations(client: ZowietekClient) -> None:
    # Get current state
    current_output = await client.async_get_output_info()
    original_loop_out = current_output.get("loop_out_on_off", "off")

    # Make change
    new_value = "on" if original_loop_out == "off" else "off"
    await client.async_set_loop_out(new_value == "on")

    # Verify change
    updated = await client.async_get_output_info()
    assert updated.get("loop_out_on_off") == new_value

    # Restore original
    await client.async_set_loop_out(original_loop_out == "on")

    # Verify restored
    final = await client.async_get_output_info()
    assert final.get("loop_out_on_off") == original_loop_out

    print("Write operations: OK")
```

## Part 2: Home Assistant Integration Testing

### When Required

Test in dev HA instance when changing:
- `__init__.py` - Integration setup/teardown
- `config_flow.py` - Configuration UI
- `coordinator.py` - Data update coordinator
- `sensor.py`, `switch.py`, etc. - Entity platforms
- `services.py` - Custom services
- Any code affecting HA user experience

### Setup Dev HA Instance

```bash
# Create config directory if needed
mkdir -p /workspaces/homeassistant-zowietek/config

# Link custom_components
ln -sf /workspaces/homeassistant-zowietek/custom_components \
       /workspaces/homeassistant-zowietek/config/custom_components

# Create minimal configuration.yaml if not exists
cat > /workspaces/homeassistant-zowietek/config/configuration.yaml << 'EOF'
# Home Assistant Dev Configuration
default_config:

logger:
  default: info
  logs:
    custom_components.zowietek: debug
EOF
```

### Start Home Assistant

```bash
# Kill any existing instance
pkill -f "hass" || true

# Start HA (foreground for debugging, or background)
# Foreground:
hass -c /workspaces/homeassistant-zowietek/config

# Background:
hass -c /workspaces/homeassistant-zowietek/config &
```

Wait for HA to start (typically 30-60 seconds). Look for:
```
INFO (MainThread) [homeassistant.core] Starting Home Assistant
```

### Access HA UI

Open in browser: http://localhost:8123

First run will require onboarding. Complete with test account.

### Test Config Flow

1. Go to **Settings** -> **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Zowietek"
4. Enter device details:
   - Host: `$ZOWIETEK_URL` (from environment)
   - Username: `$ZOWIETEK_USERNAME`
   - Password: `$ZOWIETEK_PASSWORD`
5. Click Submit

**Verify:**
- [ ] Config flow shows correct form
- [ ] Validation works (try wrong credentials)
- [ ] Device is added successfully
- [ ] Device info shows correct details

### Test Entities

After config flow completes:

1. Go to **Settings** -> **Devices & Services** -> **Zowietek**
2. Click on the device
3. Review all entities

**Verify:**
- [ ] All expected entities are created
- [ ] Entity states show real device values
- [ ] Sensors update (wait for coordinator refresh)
- [ ] Switches toggle correctly
- [ ] Buttons trigger actions

### Check Logs

```bash
# Watch live logs
tail -f /workspaces/homeassistant-zowietek/config/home-assistant.log | grep -i zowietek

# Or check in HA UI: Settings -> System -> Logs
```

**Verify no errors:**
- [ ] No exceptions in logs
- [ ] No authentication errors
- [ ] No connection timeouts
- [ ] Coordinator updates successfully

### Test Reload/Restart

1. Go to **Settings** -> **Devices & Services** -> **Zowietek**
2. Click three dots -> **Reload**
3. Verify entities still work

```bash
# Or restart HA completely
pkill -f "hass"
hass -c /workspaces/homeassistant-zowietek/config &
```

**Verify:**
- [ ] Integration reloads without error
- [ ] Entities recover correctly
- [ ] No duplicate entities

### Cleanup

```bash
# Stop HA
pkill -f "hass"

# Remove test config entry (optional)
rm -rf /workspaces/homeassistant-zowietek/config/.storage/core.config_entries
```

## Documenting Results

After live testing, document results in the PR or issue.

**CRITICAL: NEVER include real hostnames, URLs, or IP addresses in documentation!**

This is a security requirement. Real infrastructure details must never appear in:
- Commit messages
- Pull request descriptions
- Issue comments
- Any public documentation

### Correct Format (Use This)

```markdown
## Live Testing Results

### Device Testing
- **Device:** [ZOWIETEK_URL from environment]
  - Connection: OK
  - Authentication: OK
  - All endpoints responded correctly
  - Optional endpoints (device_info, ndi_config): Gracefully handled
  - Required endpoints: OK

### Home Assistant Testing
- Config flow: OK
- Entity creation: OK
- State updates: OK
- Actions: OK
- Logs: No errors

### Summary
Live device testing passed against device(s) from environment variables.
```

### WRONG Format (Never Do This)

```markdown
## Live Testing Results

### Device Testing
- **Device:** http://zow001.company.internal.com  <-- SECURITY VIOLATION!
- **Device:** 192.168.1.100  <-- SECURITY VIOLATION!
- **Device:** zowiebox.office.example.net  <-- SECURITY VIOLATION!
```

### What You CAN Include

- Generic status (OK, FAILED, PASSED)
- Error messages (sanitized of hostnames)
- Endpoint names (video_info, ndi_config, etc.)
- Feature behavior descriptions
- Number of devices tested

### What You MUST NOT Include

- Actual hostnames or domain names
- IP addresses
- Port numbers with hosts
- Internal network topology details
- Any identifying infrastructure information

## If Live Testing Fails

1. **STOP** - Do not proceed to PR
2. **Document** - Record exact failure mode
3. **Investigate** - Check device response vs expected
4. **Update Tests** - Write failing unit test for the issue
5. **Fix** - Implement the fix
6. **Re-run** - Full test suite + live testing again

The Issue #8 Lesson: A complete API rewrite was needed because live testing revealed the entire API format was wrong, despite 100% test coverage.

## Red Flags

| Warning Sign | Action |
|--------------|--------|
| "Unit tests pass" without live test | NOT complete, run live tests |
| "Device not available" | Check env vars, ask for access |
| "Works on my machine" | Test on ALL available devices |
| "Just a small change" | ALL changes need live testing |
| "I tested it manually once" | Document the tests, make repeatable |

## The Bottom Line

**Every implementation must pass live testing before being considered complete.**

1. Check for available devices (ZOWIETEK_URL, etc.)
2. If credentials exist, test against ALL devices
3. If HA-impacting, test in dev HA instance
4. Document results in PR
5. Fix any issues found, repeat

No exceptions. No shortcuts. Live testing is mandatory.
