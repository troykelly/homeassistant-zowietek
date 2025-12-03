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

# go2rtc configuration
CONF_USE_GO2RTC = "use_go2rtc"
DEFAULT_USE_GO2RTC = True

# go2rtc domain for accessing HA's go2rtc integration data
GO2RTC_DOMAIN = "go2rtc"

# Default go2rtc settings (HA-managed instance fallbacks)
GO2RTC_DEFAULT_API_URL = "http://127.0.0.1:11984"
GO2RTC_DEFAULT_RTSP_PORT = 18554  # HA-managed uses 18554, external typically 8554

# go2rtc stream management
GO2RTC_STREAM_PREFIX = "zowietek_"
GO2RTC_STREAM_TTL = 300  # 5 minutes inactivity timeout
