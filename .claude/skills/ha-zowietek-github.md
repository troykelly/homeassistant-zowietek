---
name: ha-zowietek-github
description: GitHub operations for Zowietek integration - issues, PRs, commits
---

# GitHub Workflow

## The Iron Law

```
NO CODE CHANGES WITHOUT A LINKED GITHUB ISSUE
```

Every commit, every PR, every change must reference an issue.

## Repository

| Item | Value |
|------|-------|
| Repository | `troykelly/homeassistant-zowietek` |
| URL | https://github.com/troykelly/homeassistant-zowietek |

## Issue Labels

### Type Labels
- `bug` - Something isn't working
- `enhancement` - New feature request
- `documentation` - Documentation improvements
- `question` - Support question

### Status Labels
- `needs-triage` - Needs initial review
- `needs-info` - Waiting for more information
- `confirmed` - Bug has been reproduced
- `in-progress` - Being actively worked on

### Priority Labels
- `priority: critical` - Production breaking
- `priority: high` - Important, needs attention
- `priority: medium` - Normal priority
- `priority: low` - Nice to have

### Component Labels
- `component: api` - API client
- `component: config-flow` - Configuration flow
- `component: sensor` - Sensor entities
- `component: switch` - Switch entities

## Branch Naming

```
issue-{NUMBER}-{short-description}
```

Examples:
- `issue-42-add-video-sensor`
- `issue-17-fix-auth-timeout`
- `issue-5-config-flow-validation`

## Commit Messages

Format:
```
type(scope): short description (#ISSUE)

Longer description if needed.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

### Types
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code refactoring
- `test` - Tests
- `chore` - Maintenance
- `perf` - Performance

### Scopes
- `api` - API client
- `config-flow` - Configuration
- `sensor` - Sensors
- `switch` - Switches
- `coordinator` - Data coordinator
- `services` - Custom services

### Examples

```bash
git commit -m "$(cat <<'EOF'
feat(sensor): add video input resolution sensor (#12)

Adds a sensor entity that reports the current video input resolution
from the ZowieBox device.

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

## Pull Request Format

```markdown
## Summary
- Brief description of changes
- What problem this solves

## Changes
- List of specific changes made

## Testing
- How the changes were tested
- Any manual testing performed

## Checklist
- [ ] Tests pass locally
- [ ] Code follows project style
- [ ] Documentation updated if needed
- [ ] Linked to issue

Fixes #ISSUE_NUMBER
```

## Workflow

1. **Check for existing issue**
   ```bash
   gh issue list -R troykelly/homeassistant-zowietek
   ```

2. **Create issue if needed**
   ```bash
   gh issue create -R troykelly/homeassistant-zowietek \
     --title "Add video resolution sensor" \
     --body "..." \
     --label "enhancement,component: sensor"
   ```

3. **Create branch**
   ```bash
   git checkout -b issue-12-video-resolution-sensor
   ```

4. **Make changes with TDD**

5. **Commit with issue reference**

6. **Push and create PR**
   ```bash
   git push -u origin issue-12-video-resolution-sensor
   gh pr create --fill --body "Fixes #12"
   ```
