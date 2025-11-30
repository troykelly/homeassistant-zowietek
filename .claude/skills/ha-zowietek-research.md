---
name: ha-zowietek-research
description: Research protocol when implementation fails twice
---

# Research Protocol

## When to Trigger

**After TWO implementation failures on the same problem.**

Signs you need research:
- Test keeps failing for unexpected reasons
- Getting different errors than expected
- API behaving unexpectedly
- Home Assistant rejecting your code

## The Process

### 1. STOP Coding

Do NOT attempt a third implementation. Step back.

### 2. Document the Problem

```markdown
## Problem Summary
- What I'm trying to do: [description]
- What's happening: [actual behavior]
- What I expected: [expected behavior]

## Attempts Made
1. First attempt: [description] → [result]
2. Second attempt: [description] → [result]

## Error Messages
```
[paste exact error messages]
```

## Relevant Code
```python
[paste relevant code]
```
```

### 3. Research Sources

#### For ZowieBox API
1. Test API endpoints directly with curl
2. Check device web interface behavior
3. Look for patterns in responses

```bash
# Test endpoints
curl -s -X POST "http://device/system?option=getinfo" \
  -H "Content-Type: application/json" \
  -d '{"group":"all","user":"admin","psw":"admin"}'
```

#### For Home Assistant
1. Official documentation: https://developers.home-assistant.io/
2. HA Core source code for similar integrations
3. Other custom integrations for reference

```bash
# Find similar patterns in HA core
git clone https://github.com/home-assistant/core.git --depth 1
grep -r "your_pattern" core/homeassistant/components/
```

#### For Python/aiohttp
1. Official aiohttp documentation
2. Python typing documentation
3. pytest-aiohttp examples

### 4. Understand Before Coding

Before writing any code:
- Can you explain why your previous attempts failed?
- Do you understand the correct approach?
- Can you write pseudocode for the solution?

If NO to any of these, continue researching.

### 5. Write Test First

Once you understand the solution:
1. Write a test that captures the correct behavior
2. Verify the test fails for the right reason
3. Implement the solution
4. Verify the test passes

## Common Issues

### ZowieBox API Issues

**Authentication failures:**
- Credentials must be sent with each request
- Use `login_check_flag=1` for login endpoint
- Check `status` field in response (not HTTP status)

**Empty responses:**
- API requires `group` parameter in JSON body
- Some endpoints need specific group values

**Unexpected data:**
- API returns different structures for different device modes
- Use `NotRequired` in TypedDict for optional fields

### Home Assistant Issues

**Config flow:**
- Use `vol.Required` for required fields
- Handle `ConfigEntryNotReady` for connection issues
- Test with `pytest-homeassistant-custom-component`

**Coordinator:**
- Don't do I/O in properties
- Use `async_config_entry_first_refresh()` in setup
- Handle `UpdateFailed` exception

**Entities:**
- Use `_attr_*` pattern for attributes
- Set `_attr_has_entity_name = True`
- Include `device_info` for device grouping
