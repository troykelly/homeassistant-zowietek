#!/usr/bin/env bash
# Post-start command for Home Assistant custom integration development
# This script runs each time the container starts

set -e

# Activate the Home Assistant virtual environment
export PATH="/home/vscode/.local/ha-venv/bin:$PATH"

# Ensure custom_components symlink is up to date
WORKSPACE_DIR="/workspaces/homeassistant-zowietek"
CONFIG_DIR="${WORKSPACE_DIR}/config"
if [ -d "${WORKSPACE_DIR}/custom_components" ]; then
    mkdir -p "${CONFIG_DIR}/custom_components"
    ln -sf "${WORKSPACE_DIR}/custom_components"/* "${CONFIG_DIR}/custom_components/" 2>/dev/null || true
fi

# Update development dependencies if requirements changed
if [ -f "pyproject.toml" ]; then
    uv pip install -e ".[dev]" 2>/dev/null || uv pip install -e . 2>/dev/null || true
fi

echo "Dev container started. Use 'ha' to start Home Assistant or 'pytest' to run tests."
