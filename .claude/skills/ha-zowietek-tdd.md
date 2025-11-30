---
name: ha-zowietek-tdd
description: Enforces strict TDD with RED-GREEN-REFACTOR cycle for Zowietek integration
---

# The Iron Law of TDD

**NO CODE WITHOUT A FAILING TEST FIRST**

This is not a guideline. This is not optional. This is **THE LAW**.

## RED-GREEN-REFACTOR Cycle

### 1. RED - Write Failing Test

```python
# tests/test_api.py
async def test_login_success(mock_aiohttp_session: MagicMock) -> None:
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

Run the test. **It MUST fail.** If it passes:
- The feature already exists (don't write duplicate code)
- Your test is wrong (fix it)
- You're testing the wrong thing (rethink)

### 2. GREEN - Minimal Implementation

Write the **minimum code** to make the test pass:

```python
# custom_components/zowietek/api.py
class ZowietekClient:
    async def login(self) -> bool:
        async with self._session.post(
            f"{self._host}/system?option=setinfo&login_check_flag=1",
            json={"group": "user", "user": self._username, "psw": self._password}
        ) as response:
            data = await response.json()
            return data.get("status") == "00000"
```

**STOP** when the test passes. Don't add features. Don't optimize.

### 3. REFACTOR - Clean Up

Now improve the code while keeping tests green:

- Extract methods
- Improve naming
- Add error handling (with tests first!)
- Optimize

## No Exceptions

**Q: "This function is so simple it doesn't need a test."**
A: Write a test anyway. Simple functions become complex. Tests catch regressions.

**Q: "It's just a config constant."**
A: Constants don't need tests. But if you're writing logic, test it.

**Q: "I know this works, I tested it manually."**
A: Manual tests don't run in CI. Write an automated test.

**Q: "The test would be the same as the implementation."**
A: Then your implementation is probably too simple. Test the behavior, not the code.

## Test Structure

```python
"""Tests for ZowieBox API client."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from custom_components.zowietek.api import ZowietekClient
from custom_components.zowietek.exceptions import ZowietekAuthError


class TestZowietekClientLogin:
    """Tests for ZowietekClient.login method."""

    async def test_login_success(self, mock_session: MagicMock) -> None:
        """Test successful authentication."""
        # Arrange
        mock_session.post.return_value.__aenter__.return_value.json.return_value = {
            "status": "00000",
            "rsp": "succeed"
        }

        # Act
        client = ZowietekClient("http://test", "admin", "admin")
        result = await client.login()

        # Assert
        assert result is True

    async def test_login_invalid_credentials(self, mock_session: MagicMock) -> None:
        """Test authentication failure with wrong credentials."""
        mock_session.post.return_value.__aenter__.return_value.json.return_value = {
            "status": "80003",
            "rsp": "not login"
        }

        client = ZowietekClient("http://test", "admin", "wrong")

        with pytest.raises(ZowietekAuthError):
            await client.login()
```

## Coverage Requirements

- **100% coverage required**
- No `# pragma: no cover` without justification
- All branches tested
- All error paths tested
