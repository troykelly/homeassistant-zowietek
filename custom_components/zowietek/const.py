"""Constants for the Zowietek integration."""

from __future__ import annotations

DOMAIN = "zowietek"

# API Status Codes
STATUS_SUCCESS = "00000"
STATUS_INVALID_PARAMS = "00003"
STATUS_NOT_LOGGED_IN = "80003"

# Configuration keys
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Scan interval limits (in seconds)
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300
