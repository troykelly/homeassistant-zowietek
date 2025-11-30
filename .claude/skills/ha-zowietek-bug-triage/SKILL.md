---
name: ha-zowietek-bug-triage
description: Use when investigating bugs that need reproduction - covers local HA/ZowieBox testing, evidence gathering, root cause analysis, and updating issues with findings and fix recommendations.
---

# Home Assistant Zowietek Bug Triage

## Overview

**Systematic investigation of bug reports to confirm, diagnose, and prepare fix recommendations.**

This skill covers reproducing bugs locally, gathering evidence, performing root cause analysis, and updating GitHub issues with findings.

## When to Use

- Issue has `bug` label but NOT `confirmed`
- Issue has `ai-triaged` and needs investigation
- Routed here by `ha-zowietek-issue-selector`
- User asks to "investigate" or "reproduce" a bug

## The Investigation Workflow

```
+------------------------------------------------------------------+
|                    BUG TRIAGE WORKFLOW                            |
+------------------------------------------------------------------+
|                                                                   |
|  1. PARSE ISSUE                                                   |
|     Extract: versions, steps, logs                                |
|                                                                   |
|  2. SETUP ENVIRONMENT                                             |
|     Start HA, connect ZowieBox, match reporter config             |
|                                                                   |
|  3. REPRODUCE                                                     |
|     Follow exact steps, document results                          |
|                                                                   |
|  4. GATHER EVIDENCE                                               |
|     Logs, API traces, screenshots, diagnostics                    |
|                                                                   |
|  5. ROOT CAUSE ANALYSIS                                           |
|     Trace code path, identify failure point                       |
|                                                                   |
|  6. UPDATE ISSUE                                                  |
|     Add findings, labels, fix recommendation                      |
|                                                                   |
|  7. DECIDE NEXT STEP                                              |
|     Fix now? Defer? Need more info?                               |
|                                                                   |
+------------------------------------------------------------------+
```

## Step 1: Parse Issue Data

Read the issue and extract key information:

```bash
# Get full issue details
gh issue view {N} --json title,body,labels,comments
```

**Extract from issue body:**

| Field | Description | Example |
|-------|-------------|---------|
| Integration Version | Version in manifest.json | 0.1.0 |
| HA Version | Home Assistant version | 2025.11.x |
| ZowieBox Firmware | Device firmware version | 1.0.x |
| Bug Description | What's happening | Sensor not updating |
| Expected Behavior | What should happen | Should update every 30s |
| Reproduction Steps | How to reproduce | 1. Add device, 2. Wait... |
| Debug Logs | Log output | [log content] |

**Document what's missing:**
- No debug logs? -> May need to request
- Vague steps? -> May need clarification
- Old version? -> May be fixed already

## Step 2: Setup Local Environment

### Home Assistant Devcontainer

```bash
# HA is available at localhost:8123 in devcontainer
# Check if running
curl -s http://localhost:8123/api/ | head -1
```

**Environment Variables (from .env):**
```bash
# Required for ZowieBox testing
ZOWIETEK_URL=http://zow001.signage.sy3.aperim.net
ZOWIETEK_USERNAME=admin
ZOWIETEK_PASSWORD=admin

# Required for HA API access
HOMEASSISTANT_URL=http://localhost:8123
HOMEASSISTANT_TOKEN=<from HA profile>
```

### Enable Debug Logging

Add to HA configuration or via UI:

```yaml
logger:
  default: warning
  logs:
    custom_components.zowietek: debug
    custom_components.zowietek.api: debug
    custom_components.zowietek.coordinator: debug
```

## Step 3: Reproduce the Bug

### Follow Exact Steps

Read reproduction steps from issue and follow **exactly**:

```
Reporter's steps:
1. Add ZowieBox device via integration
2. Check video resolution sensor
3. Change resolution on device
4. Sensor doesn't update

My reproduction:
1. Added device via integration
2. Video resolution shows "1920x1080"
3. Changed resolution on device to 4K
4. RESULT: Sensor still shows 1920x1080 / Sensor updated correctly
```

### Document Results

| Outcome | Next Step |
|---------|-----------|
| **Reproduced** | Proceed to evidence gathering |
| **Partially reproduced** | Note differences, may be timing/env dependent |
| **Cannot reproduce** | Document environment differences, may need more info |

## Step 4: Gather Evidence

### Debug Logs

```bash
# From HA: Settings -> System -> Logs
# Or download via API:
curl -H "Authorization: Bearer $HOMEASSISTANT_TOKEN" \
  "$HOMEASSISTANT_URL/api/error_log"
```

**What to look for:**
- Exceptions and tracebacks
- Warning messages
- API errors
- Unexpected state transitions

### API Traces

```bash
# Test ZowieBox API directly
curl -X POST "http://zow001.signage.sy3.aperim.net/video?option=getinfo" \
  -H "Content-Type: application/json" \
  -d '{"group":"all","user":"admin","psw":"admin"}'

# Compare with what integration receives
```

### Diagnostics Download

```
Settings -> Devices & Services -> Zowietek -> ... -> Download diagnostics
```

## Step 5: Root Cause Analysis

### Trace the Code Path

1. **Identify the entry point:**
   - Coordinator update? -> `coordinator.py`
   - Entity property? -> `sensor.py`
   - API call? -> `api.py`

2. **Follow the execution:**
   ```python
   # Example: Tracing video_resolution sensor
   # sensor.py:native_value
   #   -> coordinator.data.video.get("resolution")
   #     -> coordinator._async_update_data()
   #       -> client.async_get_video_info()
   ```

3. **Identify failure point:**
   - API returns unexpected data?
   - State not updated?
   - Exception thrown?
   - Wrong data parsing?

### Common Root Causes

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| State not updating | Coordinator interval | coordinator.py update_interval |
| Wrong data | API parsing error | Check TypedDict field names |
| Auth errors | Session expired | Check login flow |
| Intermittent failures | Race condition | Async timing |

## Step 6: Update Issue

### Add Investigation Comment

```bash
gh issue comment {N} --body "$(cat <<'EOF'
## Investigation Results

### Environment
- **HA Version:** 2025.11.x (devcontainer)
- **Integration Version:** 0.1.0
- **ZowieBox Firmware:** 1.0.x
- **Device Tested:** zow001

### Reproduction
- **Status:** Confirmed
- **Steps followed:** As reported
- **Behavior observed:** [Exact behavior seen]

### Evidence

<details>
<summary>Debug Logs</summary>

```
[relevant log excerpts]
```

</details>

### Root Cause Analysis

**Failure Point:** `coordinator.py:45` in `_async_update_data()`

**Cause:** The video info API response uses different field names than expected.

**Code Path:**
1. Coordinator calls `client.async_get_video_info()`
2. API returns `{"video_res": "3840x2160"}`
3. Code expects `{"resolution": "3840x2160"}`
4. Field not found, returns None

### Recommended Fix

**Approach:** Update TypedDict and parsing to match actual API response.

**Files to Change:**
- `custom_components/zowietek/api.py` - Update response handling
- `custom_components/zowietek/models.py` - Update TypedDict

**Complexity:** Low

### Test Cases Needed
- [ ] Test correct field name parsing
- [ ] Test with actual device response
EOF
)"
```

### Update Labels

```bash
# Add confirmed label
gh issue edit {N} --add-label "confirmed"

# Remove investigation-related labels
gh issue edit {N} --remove-label "needs-reproduction"

# Add component label if not present
gh issue edit {N} --add-label "component: api"
```

## Step 7: Decide Next Step

| Situation | Action |
|-----------|--------|
| Bug confirmed, fix is clear | -> Use `ha-zowietek-issue-executor` to implement fix |
| Bug confirmed, complex fix | -> Add detailed plan to issue, may need breakdown |
| Cannot reproduce | -> Request more info, add `needs-info` label |
| Upstream issue | -> Add `upstream` label, explain to reporter |

### Route to Implementation

If proceeding to fix:

```bash
# Update status
gh issue edit {N} --remove-label "status: investigating"
gh issue edit {N} --add-label "status: in-progress"

# Announce transition
gh issue comment {N} --body "Investigation complete. Proceeding to implementation."
```

Then use `ha-zowietek-issue-executor` skill.

## The Bottom Line

1. **Parse issue thoroughly** - Don't miss details
2. **Match reporter's environment** - As close as possible
3. **Follow exact steps** - Don't assume
4. **Document everything** - Logs, traces
5. **Find root cause** - Don't just describe symptoms
6. **Update issue completely** - Findings, recommendation, next steps
7. **Route appropriately** - Fix now or gather more info
