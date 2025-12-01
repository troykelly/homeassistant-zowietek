---
name: ha-zowietek-issue-executor
description: Use when implementing fixes or features from GitHub issues - autonomous execution with TDD, memory persistence, code review, and branch management. Works until issue complete or blocked.
---

# Home Assistant Zowietek Issue Executor

## Overview

**Autonomous implementation of GitHub issues using TDD, with proper branch management and PR linking.**

This skill orchestrates the complete implementation of a bug fix or feature from a GitHub issue, including TDD cycles, code review, and PR creation.

**CRITICAL: Work autonomously. Never go interactive unless you have a specific blocking question.**

## When to Use

- Issue has `confirmed` label (bug ready to fix)
- Issue has `enhancement` label (feature to implement)
- Routed here by `ha-zowietek-issue-selector`
- User asks to "fix", "implement", or "work on" an issue

## The Autonomous Workflow

```
+------------------------------------------------------------------+
|                   ISSUE EXECUTOR WORKFLOW                         |
+------------------------------------------------------------------+
|                                                                   |
|  1. CONTEXT RECOVERY                                              |
|     Check memory, read issue, check for existing work             |
|                                                                   |
|  2. BRANCH CREATION                                               |
|     Create issue-{N}-{description} branch                         |
|                                                                   |
|  3. UPDATE ISSUE STATUS                                           |
|     Add "status: in-progress" label                               |
|                                                                   |
|  4. TDD IMPLEMENTATION                                            |
|     RED -> GREEN -> REFACTOR (use ha-zowietek-tdd skill)          |
|                                                                   |
|  5. CODE REVIEW                                                   |
|     Self-review all changes                                       |
|                                                                   |
|  6. FULL TEST SUITE                                               |
|     pytest, mypy, ruff - ALL must pass                            |
|                                                                   |
|  7. LIVE DEVICE TESTING (MANDATORY)                               |
|     Test against ZowieBox devices if credentials available        |
|     Test in dev HA instance if HA-impacting changes               |
|                                                                   |
|  8. CREATE PR                                                     |
|     Link to issue with "Fixes #N"                                 |
|                                                                   |
|  9. UPDATE MEMORY                                                 |
|     Record completion for future sessions                         |
|                                                                   |
+------------------------------------------------------------------+
```

## Step 1: Context Recovery

**ALWAYS start here - even if you think you know the context.**

### Check Episodic Memory

Search for prior work on this issue:
- Previous session progress?
- Decisions already made?
- Blockers encountered?

### Read the Issue

```bash
# Get full issue details
gh issue view {N} --json title,body,labels,comments,assignees

# Check for linked PRs
gh pr list --search "#{N}"
```

**Extract from issue:**
- Problem description
- Expected behavior
- Root cause (if from bug-triage)
- Recommended fix approach
- Files to change
- Test cases needed

### Check Git Status

```bash
# Current branch
git branch --show-current

# Any existing work?
git branch -a | grep "issue-{N}"

# Uncommitted changes?
git status
```

**If work already exists:** Resume from last checkpoint.

## Step 2: Branch Creation

```bash
# Ensure on main and up to date
git checkout main
git pull origin main

# Create issue branch
git checkout -b issue-{N}-{short-description}
```

**Branch naming:**
- `issue-42-fix-video-sensor`
- `issue-123-add-stream-switch`
- `issue-7-config-flow-validation`

## Step 3: Update Issue Status

```bash
# Add in-progress status
gh issue edit {N} --add-label "status: in-progress"

# Remove investigating if present
gh issue edit {N} --remove-label "status: investigating"

# Comment that work is starting
gh issue comment {N} --body "Starting implementation."
```

## Step 4: TDD Implementation

**Use `ha-zowietek-tdd` skill. No exceptions.**

### RED - Write Failing Test

```python
# tests/test_file.py
async def test_feature_behavior(
    hass: HomeAssistant,
    mock_zowietek_client: MagicMock,
) -> None:
    """Test description matching issue requirement."""
    # Arrange
    ...
    # Act
    result = await feature()
    # Assert
    assert result == expected
```

```bash
# Run test - MUST FAIL
pytest tests/test_file.py::test_feature_behavior -v
```

**Commit:**
```bash
git add tests/
git commit -m "test(scope): RED - add failing test for feature (#N)

- Test: test_feature_behavior
- Expected: [what test expects]
- Status: Failing (TDD RED phase)"
```

### GREEN - Write Implementation

Write **minimal** code to pass the test:

```python
# custom_components/zowietek/file.py
async def feature() -> Result:
    """Implementation."""
    return Result(...)
```

```bash
# Run test - MUST PASS
pytest tests/test_file.py::test_feature_behavior -v
```

**Commit:**
```bash
git add .
git commit -m "feat(scope): GREEN - implement feature (#N)

- Implementation: [brief description]
- Test: test_feature_behavior now passing"
```

### REFACTOR - Improve Code

Only refactor while tests pass. Keep them passing.

```bash
# Verify tests still pass
pytest tests/ -v
```

**Commit (if changes made):**
```bash
git add .
git commit -m "refactor(scope): improve implementation (#N)

- Changes: [what was improved]
- Tests: All passing"
```

### Repeat for Each Requirement

Multiple features? Multiple TDD cycles:
- RED -> GREEN -> REFACTOR for requirement 1
- RED -> GREEN -> REFACTOR for requirement 2
- ...

## Step 5: Code Review

### Self-Review Checklist

| Category | Check |
|----------|-------|
| **Types** | No `Any` (except required HA overrides) |
| **Docstrings** | Google-style on all public functions |
| **Error handling** | All exceptions caught and handled |
| **Logging** | Appropriate levels, no sensitive data |
| **Style** | Passes ruff, follows conventions |

### Test Review Checklist

| Category | Check |
|----------|-------|
| **Coverage** | All code paths tested |
| **Assertions** | Meaningful, specific assertions |
| **Mocking** | Appropriate use, not over-mocked |
| **Edge cases** | Error conditions, boundaries |
| **Naming** | Descriptive test names |

**Implement ALL recommendations immediately.**

## Step 6: Full Test Suite

```bash
# Run complete test suite
pytest tests/ --cov=custom_components.zowietek --cov-report=term-missing --cov-fail-under=100

# Run type checking
mypy custom_components/zowietek/

# Run linting
ruff check custom_components/zowietek/ tests/
ruff format --check custom_components/zowietek/ tests/
```

**ALL tests must pass. ALL issues must be resolved.**

There is NO SUCH THING as an "unrelated" issue. If it's failing, fix it.

### If Tests Fail

1. Diagnose failure (use `ha-zowietek-research` skill if stuck after 2 attempts)
2. Fix the issue
3. Repeat code review for the fix
4. Re-run full test suite
5. Loop until all green

## Step 7: Live Device Testing (MANDATORY)

**Unit tests are NOT sufficient. Live testing is MANDATORY.**

Issue #8 proved this: the original API client had 100% test coverage, all tests passing - but was completely broken against real devices.

### Check for Available Devices

```python
import os
zowietek_url = os.environ.get("ZOWIETEK_URL")
zowietek_username = os.environ.get("ZOWIETEK_USERNAME")
zowietek_password = os.environ.get("ZOWIETEK_PASSWORD")
```

### If Credentials Exist: Test API Changes

For any changes to `api.py` or code that calls the API:

```python
import asyncio
import aiohttp
import os
from custom_components.zowietek.api import ZowietekClient

async def test_live():
    async with aiohttp.ClientSession() as session:
        client = ZowietekClient(
            host=os.environ["ZOWIETEK_URL"],
            username=os.environ["ZOWIETEK_USERNAME"],
            password=os.environ["ZOWIETEK_PASSWORD"],
            session=session,
        )
        # Test affected methods
        result = await client.async_get_system_time()
        print(f"Result: {result}")

asyncio.run(test_live())
```

Test against ALL available devices (check for `ZOWIETEK_URL_2`, etc.).

### If HA-Impacting Changes: Test in Dev HA

For changes to config flow, coordinator, entities, or services:

1. **Prepare configuration:**
   ```bash
   # Create config directory if needed
   mkdir -p /workspaces/homeassistant-zowietek/config

   # Ensure custom_components is linked
   ln -sf /workspaces/homeassistant-zowietek/custom_components \
          /workspaces/homeassistant-zowietek/config/custom_components
   ```

2. **Start Home Assistant:**
   ```bash
   # Kill existing instance if running
   pkill -f "hass" || true

   # Start HA in background
   hass -c /workspaces/homeassistant-zowietek/config &

   # Wait for startup
   sleep 30
   ```

3. **Test via UI:**
   - Open http://localhost:8123
   - Settings → Devices & Services → Add Integration
   - Search for "Zowietek"
   - Enter device URL and credentials
   - Verify setup completes without errors

4. **Verify functionality:**
   - Check entities appear correctly
   - Verify states update from device
   - Test any switches/buttons work
   - Check logs: `tail -f config/home-assistant.log | grep -i zowietek`

5. **Cleanup:**
   ```bash
   # Stop HA when done
   pkill -f "hass"
   ```

### What to Report

After live testing, update the issue or PR with:

- Number of devices tested (NOT the actual URLs/hostnames!)
- All methods/features tested
- Any discrepancies between mock and real behavior
- HA integration test results (if applicable)

**CRITICAL: NEVER include real hostnames, URLs, or IP addresses!**

This is a security requirement. Use generic references like:
- "Tested against device from ZOWIETEK_URL environment variable"
- "Live testing passed on 1 device"
- "All endpoints responded correctly"

Do NOT write actual hostnames like "zow001.company.com" - this leaks infrastructure details.

### If Live Testing Reveals Issues

1. **Do NOT proceed to PR creation**
2. Go back to Step 4 (TDD)
3. Write a failing test that captures the live issue
4. Fix the implementation
5. Re-run full test suite
6. Re-run live testing
7. Loop until live testing passes

See skill: `ha-zowietek-live-testing` for detailed procedures.

## Step 8: Create Pull Request

```bash
# Push branch
git push -u origin issue-{N}-{description}

# Create PR with issue link
gh pr create \
  --title "Fix: Brief description of fix" \
  --body "$(cat <<'EOF'
## Summary

Brief description of what this PR does.

Fixes #N

## Changes

- Change 1
- Change 2
- Change 3

## Test Plan

- [x] Unit tests added/updated
- [x] All tests passing (100% coverage)
- [x] Live device testing completed
- [x] HA integration testing completed (if applicable)

## Live Testing Results

- Tested against: [ZOWIETEK_URL from environment - NEVER include actual hostnames!]
- All API calls successful
- HA entities functioning correctly

## Breaking Changes

None / List any breaking changes

---
Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Critical:** The `Fixes #N` line auto-closes the issue when PR merges.

## Step 9: Update Memory

Record for future sessions:
- Issue completed
- Approach taken
- Any decisions made
- Any issues encountered

## Commit Message Format

```
type(scope): description (#issue)

- Detail 1
- Detail 2

[optional body]
```

**Types:** `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `perf`

**Scopes:** `api`, `sensor`, `switch`, `config-flow`, `coordinator`, `services`

**Examples:**
```
fix(api): handle authentication timeout (#42)

- Add retry logic for auth failures
- Clear session on 80003 status

test(sensor): add video resolution edge cases (#7)

- Test 4K resolution parsing
- Test invalid resolution handling
```

## Related Skills

This skill works with other skills. Reference them for specific guidance:

| Situation | Skill | Key Sections |
|-----------|-------|--------------|
| Writing ANY code | `ha-zowietek-tdd` | RED-GREEN-REFACTOR cycle |
| Type annotations | `ha-zowietek-typing` | TypedDict patterns, no `Any` |
| Failed twice | `ha-zowietek-research` | Research protocol |
| HA patterns | `ha-zowietek-integration` | Config flow, coordinator, entities |
| Video encoder | `ha-zowietek-video-encoder` | ZowieBox specifics |
| GitHub operations | `ha-zowietek-github` | Commit format, branch naming, labels |
| Before marking complete | `ha-zowietek-live-testing` | Device testing, HA testing procedures |

## Red Flags - STOP and Reassess

If you encounter any of these, pause and think:

- About to write code without a test -> Use TDD
- Test passes on first run -> Test is wrong
- Tempted to skip review -> Review is mandatory
- "This is unrelated" -> No such thing, fix it
- About to ask user a question -> Is it truly blocking?
- Skipping a recommendation -> ALL recommendations implemented
- No issue number in commit -> VIOLATION

## Handling Blockers

If truly blocked:

```bash
# Update issue with blocker
gh issue comment {N} --body "Blocked: [description of blocker]"
gh issue edit {N} --add-label "status: blocked"

# Remove in-progress
gh issue edit {N} --remove-label "status: in-progress"
```

Then either:
- Ask user for guidance
- Switch to different issue

## The Bottom Line

**Work autonomously until blocked or issue complete.**

1. Check memory first
2. Read issue thoroughly
3. Create branch with issue number
4. TDD always - RED -> GREEN -> REFACTOR
5. Commit with issue reference (#N)
6. Review everything
7. Fix ALL issues
8. Create PR with `Fixes #N`
9. Update memory

No shortcuts. No skipping steps. No "I'll do it later."
