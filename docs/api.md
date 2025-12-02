# ZowieTek Device HTTP API Reference

## 1. Overview

ZowieTek devices expose a JSON-over-HTTP API for configuration and control:

- **Base URL:** `http://<device-ip>/`
- **Method:** Almost all operations use POST.
- **Common query parameters:**
  - `option=getinfo` – read/query
  - `option=setinfo` – write/modify
  - `login_check_flag=1` – enforce login/session check

**Common JSON envelope (request):**

```json
{
  "group": "<module>",
  "opt": "<operation>",
  "data": { /* parameters */ },
  "opid": 3,
  "point": { "x_percent": 500, "y_percent": 500, "d_pixel": 20 }
}
```

**Common JSON envelope (response):**

```json
{
  "status": "00000",
  "rsp": "succeed",
  "data": { /* result fields */ }
}
```

### 1.1 Status codes

`status` is a string code; `"00000"` means success. Non-zero codes indicate specific errors.

| Code | Meaning (summary) |
|------|-------------------|
| `00000` | Operation succeeded |
| `000000` | Operation succeeded (alternate format, 6 zeros - used by some endpoints like `set_ndi_info`) |
| `00002` | Program not ready |
| `00003` | Required parameter missing |
| `00004` | Product not supported for this operation |
| `10000` | MPP restart (device is restarting media processing pipeline - treat as success) |
| `50001+` | NDI activation / configuration problems |
| `60001+` | Streaming URL errors (exists, invalid, protocol) |
| `70001+` | Network / Wi-Fi / port conflicts |
| `80001+` | User / auth / file format errors |

Always check `status` before trusting `data`.

---

## 2. Authentication & Accounts

All account operations are under `/system`.

### 2.1 Add user

- **Devices:** ZowieBox, ZowieCam, ZowiePTZ
- **Endpoint:** `POST /system?option=setinfo&login_check_flag=1`
- **Body:**

```json
{
  "group": "account",
  "opt": "add_account_info",
  "data": {
    "type": 1,
    "username": "user1",
    "password": "user1"
  }
}
```

Type values: `0` = admin, `1` = super, `2` = basic

### 2.2 Modify user

- **opt:** `"update_account_by_id"`
- **data:** `type`, `username`, `password`, `index` (user index)

### 2.3 Delete user

- **opt:** `"del_account_by_id"`
- **data:** `index` (user index)

### 2.4 Login

- **opt:** `"login_account"`
- **data:** `username`, `password`
- **Response data:**
  - `uuid`: session identifier (needed for logout)
  - `type`: permission level (0/1/2)

### 2.5 Logout

- **opt:** `"logout_account"`
- **data:** `uuid`, `username`

### 2.6 Verify account

- **opt:** `"verify_account"`
- **data:** `username`, `password`
- Checks existence, password, and whether the account has admin rights.

---

## 3. Common Request Pattern

Most modules follow the same pattern:

- **Read:** `POST /<module>?option=getinfo&login_check_flag=1`
  with `{"group": "<group>", "opt": "<get_...>"}`
- **Write:** `POST /<module>?option=setinfo&login_check_flag=1`
  with `{"group": "<group>", "opt": "<set_...>", "data": { ... }}`

**Modules:**

- `/video` – HDMI, encoding, NDI
- `/ptz` – PTZ config & control
- `/streamplay` – decoder & NDI decode
- `/audio` – audio settings
- `/stream` – streaming outputs
- `/ap`, `/lan`, `/wifi`, `/port`, `/mdns`, `/storage`, `/system`, etc.

---

## 4. Input / Output (HDMI)

All HDMI I/O calls use `/video` with `group: "hdmi"`.

### 4.1 Input signal detection

- **Devices:** ZowieBox
- **Endpoint:** `POST /video?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "hdmi", "opt": "get_input_info" }
```

- **Response data fields:**
  - `hdmi_signal` (0/1) – signal present
  - `audio_signal` (0 / 32000 / 44100 / 48000) – sample rate or 0 for none
  - `width`, `height` – resolution
  - `framerate` – frame rate
  - `desc` – human-readable resolution string

### 4.2 Set output configuration

- **Devices:** ZowieBox, ZowieCam, ZowiePTZ
- **Endpoint:** `POST /video?option=setinfo&login_check_flag=1`
- **Body:**

```json
{
  "group": "hdmi",
  "opt": "set_output_info",
  "data": {
    "format": "2160p30",
    "audio_switch": 1,
    "loop_out_switch": 0
  }
}
```

Fields:

- `format` – resolution string (e.g., "2160p30", "1080p60")
- `audio_switch` – 0: mute, 1: unmute
- `loop_out_switch` – 0: output (normal), 1: loop out (ZowieBox)

### 4.3 Get output configuration

- **Endpoint:** `POST /video?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "hdmi", "opt": "get_output_info" }
```

- **Response data highlights:**
  - `switch` – output enable
  - `disp_dev.selected_id` + `disp_dev_list` – output device (LCD / HDMI / SDI)
  - `format` – resolution (same set as above)
  - `audio_switch`, `loop_out_switch`
  - `bufnum`, `auto_follow`

---

## 5. PTZ Camera Configuration (ZowieBox)

These calls configure how ZowieBox talks to an external PTZ camera (VISCA / Pelco / ONVIF).

### 5.1 Get PTZ configuration

- **Devices:** ZowieBox
- **Endpoint:** `POST /ptz?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "ptz", "opt": "get_ptz_info" }
```

- **Response data (high-level):**
  - `protocol` – current protocol id (auto / VISCA over IP / ONVIF / VISCA / Pelco-D / Pelco-P)
  - `protocol_list` – available protocol entries, including IP, port, address, baud, etc.
  - `usb2serial` – USB serial presence flag

### 5.2 Set PTZ configuration

- **Endpoint:** `POST /ptz?option=setinfo&login_check_flag=1`
- **Body:**

```json
{
  "group": "ptz",
  "opt": "set_ptz_info",
  "data": {
    "protocol": 1,
    "type": 0,
    "ip": "192.168.1.167",
    "port": 1259,
    "addr": 1,
    "addr_fix": 0,
    "baudrate_id": 2
  }
}
```

**Key fields:**

- `protocol` – 0 (auto, ZowiePTZ only), 1 (VISCA over IP), 3 (VISCA), 4 (Pelco-D), 5 (Pelco-P)
- `type` – 0: TCP, 1: UDP (when applicable)
- `baudrate_id` – 0: 2400, 1: 4800, 2: 9600, 3: 11920, 4: 38400
- `addr` – 1–7 for VISCA over IP / VISCA, 0–255 for Pelco-D/P
- `usb2serial` – 0 if USB serial present, 1 if not

---

## 6. PTZ Motion & Focus Control (ZowiePTZ / ZowieCam)

### 6.1 PTZ motion (opt: "control")

- **Devices:** ZowiePTZ
- **Endpoint:** `POST /ptz?option=setinfo&login_check_flag=1`
- **Base body:**

```json
{
  "group": "ptz",
  "opt": "control",
  "opid": 3,
  "data": { },
  "point": { }
}
```

**Commonly used opid values:**

| opid | Action (summary) |
|------|------------------|
| 3 | Pan left (step) |
| 4 | Pan left (continuous) |
| 1 | Pan right (step) |
| 2 | Pan right (continuous) |
| 7 | Tilt up (step) |
| 8 | Tilt up (continuous) |
| 9 | Tilt down (step) |
| 10 | Tilt down (continuous) |
| 5 | Go to horizontal position (`data.value` 0–8000) |
| 11 | Go to vertical position (`data.value` 0–2100) |
| 19 | Focus near (step) |
| 21 | Focus far (step) |
| 20 | Focus near (continuous) |
| 22 | Focus far (continuous) |
| 25 | One-touch autofocus at a point (`point`) |
| 26 | Save preset (`data.id`, `data.desc`) |
| 29 | Recall preset (`data.id`) |
| 30 | Delete preset (`data.id`) |

Focus operations only work when focus mode is manual.

### 6.2 Focus mode

- **Devices:** ZowiePTZ, ZowieCam

**Get focus mode:**

- **Endpoint:** `POST /ptz?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "ptz", "opt": "get_focusmode" }
```

- **Response:** `data.selected_id`: 0 (AUTO), 1 (MANUAL), 2 (ONE_PUSH)

**Set focus mode:**

- **Endpoint:** `POST /ptz?option=setinfo&login_check_flag=1`
- **Body:**

```json
{
  "group": "ptz",
  "opt": "set_focus_mode",
  "data": { "focusmode": 0 }
}
```

Values: 0 = AUTO, 1 = MANUAL, 2 = ONE_PUSH

### 6.3 AF sensitivity, zone, lock

- `get_sensitivity` / `set_sensitivity` – AF responsiveness (high / medium / low / ultra-low)
- `get_focus_zone` / `set_focus_zone` – focus region presets
- `get_focus_speed` / `set_focus_speed` – lens drive speed
- `get_af_lock_status` / `set_af_lock_status` – enable/disable AF lock

### 6.4 Zoom & digital zoom

- `get_zoom_speed` / `set_zoom_speed` – physical zoom speed (PTZ)
- `get_digital_zoom_info` / `set_digital_zoom_info` – crop/zoom region and factor

---

## 7. Encoding (Video)

All encoding operations use `/video` with `group: "venc"`.

### 7.1 Get encoding parameters

- **Devices:** ZowieBox, ZowieCam, ZowiePTZ
- **Endpoint:** `POST /video?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "venc" }
```

- **Response `data.venc[]` per channel:**
  - `venc_chnid` – channel index
  - `codec.selected_id` + `codec_list` – H.264 / H.265 / MJPEG
  - `profile.selected_id` – BP / MP / HP
  - `ratecontrol.selected_id` – CBR / VBR
  - `bitrate` – kbps range depends on stream
  - `ndi_bitrate_pre` – NDI bitrate percentage when in NDI mode
  - `width`, `height`, `framerate`, `gop`, `keyinterval`
  - QP and rotation settings
  - `stream_id` – 0 main, 1 sub, sometimes additional snapshot stream
  - `desc` – label ("main", "sub", "snapshot")

### 7.2 Modify encoding parameters

- **Endpoint:** `POST /video?option=setinfo&login_check_flag=1`
- **Body (pattern):**

```json
{
  "group": "venc",
  "venc": [
    {
      "venc_chnid": 0,
      "codec": { "selected_id": 0 },
      "profile": { "selected_id": 0 },
      "ratecontrol": { "selected_id": 0 },
      "bitrate": 5000000,
      "ndi_bitrate_pre": 50,
      "width": 1920,
      "height": 1080,
      "framerate": 30,
      "gop": 60,
      "keyinterval": 60,
      "rotate": { "selected_id": 0 },
      "stream_id": 0,
      "desc": "main"
    }
  ]
}
```

**Note:** Encoding parameter changes require an active HDMI input signal. Returns status `10001` "HDMI no signal" if no signal is present.

---

## 8. Decoding (/streamplay)

These control the built-in decoder on ZowieBox.

All calls: `POST /streamplay?option=setinfo|getinfo&login_check_flag=1`

### 8.1 Add decoding URL

- **group:** `"streamplay"`, **opt:** `"streamplay_add"`
- **data:** e.g. `url`, `switch`, `name`, `streamtype`

### 8.2 Get decoding information

- **opt:** `"streamplay_get_all"`
- Returns all configured decode URLs and state.

### 8.3 Delete decoding URL

- **opt:** `"streamplay_del"`
- **data:** `index` (entry index from get-all call)

### 8.4 Modify decoding URL

- **opt:** `"streamplay_modify"`
- **data (summary):**
  - `index` – which URL
  - `switch` – 0 off / 1 on
  - `name` – alias
  - `streamtype` – 0 local / 1 live
  - `url` – decode URL (RTSP/RTMP etc, subject to support)

### 8.5 Get decoder state

- **opt:** `"get_decoder_state"` (group `"streamplay"`)
- **Response:** `data.decoder_state` – 0 none active, 1 some decode active

---

## 9. NDI Decoding (/streamplay, group: "streamplay_ndi")

Used to discover and select NDI sources on the LAN.

### 9.1 NDI find

- **Endpoint:** `POST /streamplay?option=setinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "streamplay_ndi", "opt": "ndi_find" }
```

### 9.2 Get all NDI sources

- **Endpoint:** `POST /streamplay?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "streamplay_ndi", "opt": "ndi_get_all" }
```

- **Response `data[]` entries:** `index`, `name`, `url`, `streamplay_status`, `bandwidth`, `framerate`, `width`, `height`

### 9.3 Enable / disable NDI decoding

- Typically via `"opt": "ndi_play"` / `"ndi_stop"`

---

## 10. NDI Encoding (/video, group: "ndi")

Controls built-in NDI|HX encoder.

### 10.1 Activate NDI

- **opt:** `"activate_ndi"` – passes activation code and stores it

### 10.2 Get NDI configuration

- **Endpoint:** `POST /video?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "ndi", "opt": "get_ndi_info" }
```

- **Response data:**
  - `activate` – activation flag
  - `switch` – NDI on/off
  - `mode_id` – 1 NDI|HX, 2 NDI|HX2, 3 NDI|HX3
  - `machinename` – NDI name
  - `groups` – NDI group string(s)
  - `multicast` – `ttl`, `enable`, `netmask`, `netprefix`

### 10.3 Set NDI configuration

- **Endpoint:** `POST /video?option=setinfo&login_check_flag=1`
- **Body pattern:**

```json
{
  "group": "ndi",
  "opt": "set_ndi_info",
  "data": {
    "switch": 1,
    "mode_id": 3,
    "machinename": "ZowieBox-12343",
    "groups": "Public,A",
    "multicast": {
      "enable": 1,
      "netmask": "255.255.0.0",
      "netprefix": "239.255.0.0",
      "ttl": 1
    }
  }
}
```

**Important Notes:**
- The complete data structure is required. Sending only partial fields (e.g., just `machinename`) will fail with status `00003`.
- First retrieve the current configuration via `get_ndi_info`, then merge your changes and send the complete structure.
- This endpoint returns status `"000000"` (6 zeros) on success instead of the typical `"00000"` (5 zeros).

### 10.4 NDI switch (simple on/off)

- **opt:** `"ndi_switch"`
- **data:** `{ "switch": 0|1 }`

---

## 11. Audio (/audio, group: "all")

Controls audio capture, encoding and output routing.

### 11.1 Get audio configuration

- **Endpoint:** `POST /audio?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "all" }
```

- **Response data highlights:**
  - Global `switch` – enable/disable audio
  - `ai_devid`, `ai_chnid[]` – audio input devices & channels
  - `ai_type` – selected input (e.g. LINE IN, Internal MIC, HDMI IN)
  - `aenc_chnnum`, `aenc_chnid[]` – encoder channels
  - `ao_devid`, `ao_devnum` – output devices
  - Stream associations via `stream_id[]`

### 11.2 Set audio configuration

- **Endpoint:** `POST /audio?option=setinfo&login_check_flag=1`
- **Body:** `group: "all"`, `opt: "set_all"`

### 11.3 Audio switch

Usually a field in the above, or a dedicated opt depending on firmware.

### 11.4 Set audio volume

- **Endpoint:** `POST /audio?option=setinfo&login_check_flag=1`
- **Body:**

```json
{
  "group": "audio",
  "volume": 75
}
```

- **Parameters:**
  - `volume`: Integer 0-100 representing the audio input volume level

**Note:** Requires active HDMI input signal. Returns status `10001` "HDMI no signal" if no signal.

**Response:**

```json
{
  "status": "00000",
  "rsp": "succeed"
}
```

---

## 12. Streaming (/stream, group: "publish")

This module manages RTSP/RTMP/SRT publish targets.

### 12.1 Get publish list

- **Endpoint:** `POST /stream?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "publish" }
```

- **Response:** `publish[]` array with entries containing:
  - `index` – stream index
  - `type` – protocol type (e.g., "rtmp", "srt")
  - `switch` – 0 off / 1 on
  - `url` – publish URL

### 12.2 Add / publish stream

- **Endpoint:** `POST /stream?option=setinfo&login_check_flag=1`
- **opt:** `"add_stream_info"` or similar
- **data:** includes URL, stream type, enabled flag, priority/order, etc.

### 12.3 Start / stop streaming

- **opt:** `"update_publish_switch"`
- **data:** `{ "index": <stream_index>, "switch": 0|1 }`
- If streaming fails, status codes `6000x` are returned.

### 12.4 Delete stream

- **opt:** `"del_stream_info"` with `data.index`

### 12.5 Modify stream order

- **opt:** `"modify_stream_order"` – reorder entries shown in UI

---

## 13. AP (Access Point) – /ap

### 13.1 Get AP configuration

- **Endpoint:** `POST /ap?option=getinfo&login_check_flag=1`
- **group:** `"ap"`, **opt:** `"get_ap_info"` – returns SSID, channel, security, etc.

### 13.2 Set AP configuration

- **Endpoint:** `POST /ap?option=setinfo&login_check_flag=1`
- **group:** `"ap"`, **opt:** `"set_ap_info"`, **data:** `{ ... }`

### 13.3 AP switch

Often a flag in the same structure (e.g. `switch: 0/1`).

---

## 14. LAN – /lan

### 14.1 Get LAN data

- **Endpoint:** `POST /lan?option=getinfo&login_check_flag=1`
- **group:** `"lan"`, **opt:** `"get_lan_info"` – returns IP mode (DHCP/static), IP/netmask/gateway, DNS etc.

### 14.2 Modify LAN configuration

- **Endpoint:** `POST /lan?option=setinfo&login_check_flag=1`
- **group:** `"lan"`, **opt:** `"set_lan_info"`, **data:** `{ ... }`

### 14.3 Check LAN connectivity

- **opt:** `"lan_connect_check"` – ping default gateway or another target

### 14.4 Detect Internet connectivity

- **opt:** `"wan_connect_check"` – tests reachability to internet host

### 14.5 Get display IP

- **opt:** `"get_display_ip"` – IP used for OSD display / UI

---

## 15. WiFi – /wifi

### 15.1 WiFi switch

- **Endpoint:** `POST /wifi?option=setinfo&login_check_flag=1`
- **group:** `"wifi"`, **opt:** `"wifi_switch"`, **data:** `{ "switch": 0|1 }`

### 15.2 Get WiFi list

- **Endpoint:** `POST /wifi?option=getinfo&login_check_flag=1`
- **group:** `"wifi"`, **opt:** `"get_scan_info"` – scans APs and returns SSID/quality/security info

### 15.3 Get WiFi connection info / status

- **opt:** `"get_wifi_info"`

### 15.4 Connect to WiFi

- **opt:** `"set_wifi_info"`
- **data:** SSID, password, security type, etc.

WiFi-related failures use `7000x` status codes (e.g. `70001` connect failed, `70002` invalid IP).

---

## 16. Port – /port

- **Get port configuration:** `get_port_info`
- **Set port configuration:** `set_port_info`

Fields include HTTP port, RTMP/RTSP ports, VISCA TCP/UDP ports, WebSocket, etc. Port conflicts map to status codes `70007`–`70015`.

---

## 17. mDNS – /mdns

- **Get mDNS info:** `group: "mdns"`, `opt: "get_mdns_info"`
- **Set mDNS info:** `opt: "set_mdns_info"` – hostname, service name, on/off

---

## 18. Device Time – /system, group: "systime"

### 18.1 Get device time

- **Endpoint:** `POST /system?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "systime", "opt": "get_systime_info" }
```

- **Response data:**
  - `time.year`, `month`, `day`, `hour`, `minute`, `second`
  - `setting_mode_id`: 0 sync with PC, 1 manual, 2 NTP
  - `time_zone_id` – "GMT±n"
  - `time_type_id` – 12/24h format
  - `ntp_enable`, `ntp_server`, `ntp_port`

### 18.2 Set device time

- **Endpoint:** `POST /system?option=setinfo&login_check_flag=1`
- **group:** `"systime"`, **opt:** `"set_systime_info"`, with data including:
  - `setting_mode_id`
  - `time` object (for manual / PC sync)
  - `time_zone_id`
  - `ntp_enable`, `ntp_server`, `ntp_port`

---

## 19. Recording & Storage – /storage

### 19.1 Get storage device status

- **Endpoint:** `POST /storage?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "storage_status" }
```

- **Response `data[]`:** one entry per storage (e.g. sdcard), with mount state, file system, capacity, used, free, etc.

### 19.2 Recording tasks

Under `/storage` with appropriate group (`"record"` or similar):

- Get recording task list
- Modify task (path, stream, schedule)
- Start / stop recording
- Get video file path(s)

---

## 20. Snapshot – /snapshot

- **Snapshot trigger:** captures a still image
- **Get photo path:** returns where snapshots are stored (filename, URL path)

---

## 21. Tally (v1) – /tally

Operations:

- `get_tally_info` – Tally parameters (mode, colours, behaviour)
- `set_tally_info` – modify settings
- `tally_switch` – turn on/off
- `get_tally_color` – returns current active colour

---

## 22. Restore & Reboot – /system

### 22.1 Reboot device

- **Endpoint:** `POST /system?option=setinfo&login_check_flag=1`
- **Body:**

```json
{
  "group": "syscontrol",
  "opt": "set_reboot_info",
  "data": {
    "command": "reboot"
  }
}
```

**Note:** The device may close the connection before responding, return an empty response, or timeout during reboot. These are expected behaviors.

### 22.2 Other system operations

Additional opt values for the `syscontrol` group:

- `factory_reset` – restore factory defaults
- `standby` – go to low-power standby
- `exit_standby` – wake from standby

---

## 23. Image Settings – /image

Sub-groups cover exposure, colour, noise reduction, AE lock, style, etc. Common pattern:

- **Get exposure:** `group: "image_exposure"`, `opt: "get_exposure"`
- **Set exposure:** `opt: "set_exposure"`

Similar for:

- Aperture (iris)
- Colour (white balance, saturation, etc.)
- Noise reduction
- Image style
- AE lock status (get/set)

Each call follows the same getinfo / setinfo pattern with a data object containing mode and numeric values.

---

## 24. Patient Case – /patient

Used on medical-focused devices.

- **Create patient information:** `group: "patient"`, `opt: "create_case"`, data with patient fields
- **Case query:** `group: "patient"`, `opt: "query_case"`, query parameters in data

---

## 25. Pan/Tilt/Zoom/Focus Control (Alternate API)

Another PTZ control interface, typically:

- Pan/Tilt control operations (direction + speed)
- Zoom control (tele/wide, continuous)
- Go home
- Preset save / recall / delete
- Focus mode set / get
- Continuous focus control

This section complements the earlier opid-based PTZ control and may target a slightly different device firmware variant.

---

## 26. Temperature – /system, group: "temperature"

- **Get CPU temperature:**

```json
{ "group": "temperature", "opt": "get_cpu_temp" }
```

Returns current CPU temperature in degrees.

---

## 27. Tally (v2)

A second, slightly different Tally API; often for ZowiePTZ / ZowieCam.

Operations (names vary slightly from section 21):

- Get Tally mode
- Turn Tally on/off
- Set Tally parameters
- Get current Tally colour

---

## 28. Putting It All Together

A typical control flow for a custom app might look like:

1. Log in via `/system` → get `uuid`
2. Discover video input via `hdmi.get_input_info`
3. Configure output (`set_output_info`) and encoding (`venc`)
4. Configure PTZ (`set_ptz_info`), then drive motion using `ptz.control` opids
5. Set up streaming targets under `/stream` or decoding under `/streamplay`
6. Enable NDI if needed via `ndi` group
7. Manage recording and snapshots via `/storage` / snapshot APIs
8. Persist user accounts, time, and network settings via `/system`, `/lan`, `/wifi`, `/ap`, `/port`, `/mdns`

---

## 29. System Attributes – /system, group: "sys_attr"

The `sys_attr` group provides comprehensive device identification information.

### 29.1 Get system attributes

- **Endpoint:** `POST /system?option=getinfo&login_check_flag=1`
- **Body:**

```json
{ "group": "sys_attr" }
```

- **Response data:**
  - `SN` – Device serial number
  - `device_name` – Device name (e.g., "ZowieBox-27117")
  - `firmware_version` – Firmware version (e.g., "2.0.0.12")
  - `hardware_version` – Hardware version (e.g., "3.1.12.22")
  - `manufacturer` – Manufacturer name ("Zowietek")
  - `model` – Device model ("ZowieBox")
  - `language_id` – Current language setting
  - `isp_version` – ISP version
  - `mcu_version` – MCU version
  - `web_version` – Web interface version
  - `ndi_version` – NDI library version
  - `app_version` – Application version
  - `ndi_activate` – NDI activation status
  - `ndi_switch` – NDI enabled status
  - `chipid` – Hardware chip ID
  - `first_use_flag` – First use indicator
  - `ui_first_use_flag` – UI first use indicator

**Note:** This is the preferred endpoint for device identification. The `devinfo` group is NOT supported by ZowieBox devices and will return "Invalid parameters: param group not support !!!"

---

## 30. Device Discovery

ZowieBox devices use a **proprietary UDP multicast discovery protocol** for automatic device detection on the local network.

### 30.1 Discovery Protocol Overview

| Parameter | Value |
|-----------|-------|
| Protocol | JSON over UDP multicast |
| Multicast Address | `224.170.1.242` |
| Port | `21007` |
| Transport | UDP |
| IP Version | **IPv4 only** |

**Note:** The discovery protocol is IPv4-only. There is no IPv6 multicast equivalent.

### 30.2 Message Types

#### 30.2.1 Keepalive

Devices periodically send keepalive messages to announce their presence.

```json
{
    "opt": "keepalive",
    "master_device_sn": "25859"
}
```

#### 30.2.2 Discovery Request

To discover devices, send a `check_devices_request` message to the multicast group.

```json
{
    "opt": "check_devices_request",
    "master_device_sn": "00000"
}
```

**Note:** The `master_device_sn` can be any value (e.g., `"00000"` or `"discovery"`). It identifies the requester and is echoed back in responses.

#### 30.2.3 Discovery Response

Devices respond to discovery requests with their configuration details.

```json
{
    "opt": "check_devices_result",
    "master_device_sn": "00000",
    "data": {
        "ip": "10.61.22.241",
        "web_port": 80,
        "product_id": 2,
        "workmode_id": 1,
        "device_sn": "27117",
        "device_name": "ZowieBox-27117"
    }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ip` | string | Device IP address |
| `web_port` | integer | HTTP API port (usually 80) |
| `product_id` | integer | Product type identifier |
| `workmode_id` | integer | Current operating mode |
| `device_sn` | string | Device serial number |
| `device_name` | string | User-configured device name |

### 30.3 Implementation Example

```python
import socket
import json

MULTICAST_GROUP = "224.170.1.242"
MULTICAST_PORT = 21007

def discover_devices(timeout: float = 3.0) -> list[dict]:
    """Discover ZowieBox devices on the network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout)

    # Join multicast group to receive responses
    import struct
    mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    # Bind to receive responses
    sock.bind(("", MULTICAST_PORT))

    # Send discovery request
    request = json.dumps({
        "opt": "check_devices_request",
        "master_device_sn": "00000"
    }).encode()
    sock.sendto(request, (MULTICAST_GROUP, MULTICAST_PORT))

    # Collect responses
    devices = []
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            msg = json.loads(data.decode())
            if msg.get("opt") == "check_devices_result":
                devices.append(msg.get("data", {}))
        except socket.timeout:
            break

    sock.close()
    return devices
```

### 30.4 Standard Discovery Protocols (Not Supported)

ZowieBox devices do **not** support standard discovery protocols:

| Protocol | Status | Notes |
|----------|--------|-------|
| SSDP (UPnP) | ❌ Not Supported | Port 1900 closed |
| mDNS/Zeroconf | ❌ Not Supported | Port 5353 closed |

### 30.5 HTTP API Device Search

The HTTP API also provides a device search endpoint (requires an existing device connection):

- **Endpoint:** `POST /system?option=getinfo&login_check_flag=1`
- **Body:**

```json
{"group": "device_search", "opt": "get_devices_list"}
```

- **Response:**

```json
{
    "rsp": "succeed",
    "status": "00000",
    "data": [
        {
            "ip": "10.61.22.241",
            "web_port": 80,
            "device_sn": "27117",
            "device_name": "ZowieBox-27117",
            "workmode_id": 1,
            "product_id": 2
        }
    ]
}
```

**Note:** This endpoint requires connecting to an existing device first, so it cannot be used for initial discovery. Use the UDP multicast protocol for zero-configuration discovery.

---

## 31. Home Assistant Device Triggers

The Zowietek integration provides device triggers that can be used in Home Assistant automations. These triggers fire events when specific device state changes occur.

### 31.1 Available Trigger Types

| Trigger | Event Type | Description |
|---------|-----------|-------------|
| `stream_started` | `zowietek_event` | Fires when any stream output (NDI, RTMP, or SRT) is enabled |
| `stream_stopped` | `zowietek_event` | Fires when all stream outputs are disabled |
| `video_input_detected` | `zowietek_event` | Fires when HDMI video signal is detected |
| `video_input_lost` | `zowietek_event` | Fires when HDMI video signal is lost |

### 31.2 Event Structure

Events are fired on the Home Assistant event bus with the following structure:

```json
{
    "event_type": "zowietek_event",
    "data": {
        "device_id": "<ha_device_id>",
        "type": "<trigger_type>"
    }
}
```

### 31.3 Using Device Triggers in Automations

Device triggers appear in the Home Assistant automation UI when creating device-based automations. Example YAML automation:

```yaml
automation:
  - alias: "Notify when video input detected"
    trigger:
      - platform: device
        domain: zowietek
        device_id: <your_device_id>
        type: video_input_detected
    action:
      - service: notify.mobile_app
        data:
          message: "Video input detected on ZowieBox"

  - alias: "Log when stream starts"
    trigger:
      - platform: device
        domain: zowietek
        device_id: <your_device_id>
        type: stream_started
    action:
      - service: logbook.log
        data:
          name: "ZowieBox"
          message: "Started streaming"
```

### 31.4 Firing Triggers Programmatically

To fire device triggers from within the integration (e.g., from the coordinator when state changes are detected), use:

```python
from homeassistant.core import HomeAssistant

hass.bus.async_fire(
    "zowietek_event",
    {
        "device_id": device_id,
        "type": "stream_started",  # or other trigger type
    }
)
```

### 31.5 Implementation Notes

- Triggers are defined in `custom_components/zowietek/device_trigger.py`
- The `async_get_triggers` function returns available triggers for a device
- The `async_attach_trigger` function attaches event listeners for the trigger
- Translations for trigger types are in `strings.json` under `device_automation.trigger_type`
