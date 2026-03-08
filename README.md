# OBS Auto Scene Switcher
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey?logo=apple)
![OBS](https://img.shields.io/badge/OBS-WebSocket%20v5-purple?logo=obsstudio&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

Automatically switches OBS scenes based on what's happening on another computer — detects PowerPoint presentation mode, active video playback, fullscreen apps, and specific application windows.

---

## How It Works

This is a two-script system:

```
[Monitored Computer] ──────────────────────► [OBS Mac]
  obs_monitor_server.py                    obs_scene_switcher_client.py
  (Mac or Windows)                         Connects to OBS via WebSocket
  Watches the screen                       Switches scenes automatically
  Sends JSON over TCP port 5555
```

- The **server** runs on the computer being monitored. It polls the active window every 0.5 seconds and streams JSON updates over your local network.
- The **client** runs on the Mac running OBS. It receives those updates and switches scenes accordingly.

---

## Scripts

| File | Runs On | Purpose |
|------|---------|---------|
| `obs_scene_switcher_client.py` | Mac running OBS | Receives updates, switches OBS scenes |
| `obs_monitor_server_mac.py` | Mac being monitored | Detects window/app state via AppleScript |
| `obs_monitor_server_windows.py` | Windows PC being monitored | Detects window/app state via Win32 API |

---

## Scene Mapping

| Detected Content | OBS Scene |
|-----------------|-----------|
| PowerPoint / Keynote in presentation mode | `Live Stream Screen Powerpoint & Video` |
| Video actively playing (VLC, QuickTime, browser, etc.) | `Powerpoint` |
| Everything else (default) | `Live Stream Screen` |

> Scene names are fully customizable at the top of the client script.

---

## Requirements

### OBS Mac (client)

Install **one** of these WebSocket libraries — the script supports both:

```bash
pip3 install obsws-python
# OR
pip3 install obs-websocket-py
```

OBS must have the WebSocket server enabled:
> OBS → Tools → WebSocket Server Settings → Enable WebSocket Server

---

### Monitored Mac (server)

No third-party libraries required — uses Python's standard library and macOS's built-in `osascript`.

**Python 3 only.**

**Accessibility permission required:**
> System Settings → Privacy & Security → Accessibility → Add Terminal (or your Python runner)

Without this, AppleScript cannot read window titles.

---

### Monitored Windows PC (server)

```bash
pip install pywin32 psutil
```

No special permissions required on Windows.

---

## Setup

### Step 1 — Start the server on the monitored computer

**Mac:**
```bash
python3 obs_monitor_server_mac.py
```

**Windows:**
```bash
python obs_monitor_server_windows.py
```

When it starts, it will print its local IP address:
```
✓ Server listening on port 5555
  Set REMOTE_HOST = '192.168.1.50' in the client script
```

---

### Step 2 — Configure the client script

Open `obs_scene_switcher_client.py` and update the configuration block at the top:

```python
REMOTE_HOST = '192.168.1.50'   # ← IP printed by the server in Step 1
REMOTE_PORT = 5555
OBS_HOST    = 'localhost'
OBS_PORT    = 4455
OBS_PASSWORD = 'your_password'  # From OBS WebSocket Server Settings

# Update these to match your actual OBS scene names exactly
POWERPOINT_PRESENTATION_SCENE = "Live Stream Screen Powerpoint & Video"
VIDEO_PLAYING_SCENE            = "Powerpoint"
DEFAULT_SCENE                  = "Live Stream Screen"
```

---

### Step 3 — Start the client on the OBS Mac

```bash
python3 obs_scene_switcher_client.py
```

Expected output:
```
============================================================
  OBS Auto Scene Switcher - PowerPoint & Video Detection
============================================================

✓ Using obsws-python library

Configuration:
  Remote computer: 192.168.1.50:5555
  OBS WebSocket: localhost:4455
  PowerPoint (presentation mode) → 'Live Stream Screen Powerpoint & Video'
  Video (actively playing)       → 'Powerpoint'
  Default (everything else)      → 'Live Stream Screen'

✓ Connected to OBS WebSocket
✓ Current scene: Live Stream Screen

Starting monitor loop...
✓ Connected to monitor server at 192.168.1.50:5555

Monitoring for content changes...

ℹ PowerPoint PRESENTATION MODE detected - Slide Show
→ Switched to scene: Live Stream Screen Powerpoint & Video
```

---

## Customization

### Adding apps to watch (Mac server)

Edit the lists at the top of `obs_monitor_server_mac.py`:

```python
# Apps that trigger the default scene when focused
DEFAULT_SCENE_APPS = [
    "Finder",
    "Safari",
    "Google Chrome",
    "Notes",
    "Your App Here",   # ← add any app by its name in Activity Monitor
]

# Apps treated as video players
VIDEO_APPS = [
    "VLC",
    "QuickTime Player",
    "IINA",
    "Infuse",          # ← add more here
]
```

### Adding apps to watch (Windows server)

Edit the lists at the top of `obs_monitor_server_windows.py`:

```python
# Use the .exe process name (visible in Task Manager → Details tab)
VIDEO_PROCESSES = [
    "vlc.exe",
    "wmplayer.exe",
    "mpc-hc64.exe",
    "yourplayer.exe",   # ← add here
]

BROWSER_VIDEO_KEYWORDS = [
    "YouTube",
    "Netflix",
    "Your Streaming Site",   # ← matches against window/tab title
]
```

### Changing the poll interval

In either server script, lower = more responsive, higher = less CPU:

```python
POLL_INTERVAL = 0.5   # seconds — change to 0.25 for faster or 1.0 for slower
```

---

## Troubleshooting

### Client can't connect to server
- Make sure the server script is running **before** starting the client
- Confirm the IP address in `REMOTE_HOST` matches the server machine
- Check that port `5555` is not blocked by a firewall on the server machine
  - **Mac:** System Settings → Network → Firewall
  - **Windows:** Windows Defender Firewall → Allow an app through firewall

### OBS won't connect
- Make sure OBS is open and WebSocket server is enabled
- Double-check the password in `OBS_PASSWORD` matches OBS exactly
- Default OBS WebSocket port is `4455`

### Scene doesn't switch
- Scene names are **case-sensitive** — copy them exactly from OBS
- Open the OBS scene list and verify the names match what's in the config

### Mac server doesn't detect window titles
- Terminal needs Accessibility permission
- Go to: **System Settings → Privacy & Security → Accessibility → Add Terminal**
- If running via a launcher or IDE, add that app instead

### PowerPoint not detected as presenting (Windows)
- Make sure you're in **Slide Show** view, not Presenter View editing mode
- The script looks for a fullscreen window or a window with "Slide Show" in the title
- Check Task Manager → Details to confirm the process name is `POWERPNT.EXE`

---

## How Detection Works

### Mac (AppleScript)
- Uses `osascript` to query `System Events` for the frontmost app name and window title
- Queries **PowerPoint** directly for Slide Show state
- Queries **Keynote** directly for `playing` document state
- Queries **VLC** and **QuickTime** directly for playback state
- Falls back to window position check (`0, 0`) for fullscreen detection

### Windows (Win32 API)
- Uses `win32gui.GetForegroundWindow()` for the active window
- Uses `psutil` to resolve PID → process name
- Enumerates all PowerPoint windows — 2+ windows = slide show is active
- Compares window rect against monitor rect for fullscreen detection
- Checks window titles for browser-based video (YouTube, Netflix, etc.)

---

## Network Architecture

```
Monitored Computer              OBS Mac
┌─────────────────┐             ┌─────────────────────┐
│  Server Script  │  TCP:5555   │   Client Script     │
│  polls screen   │────────────►│   receives JSON     │
│  every 0.5s     │             │   switches scenes   │
│                 │  JSON:      └──────────┬──────────┘
│ {"content_type":│  newline              │ WebSocket
│  "video",       │  delimited            │ :4455
│  "app_name":    │  stream               ▼
│  "VLC", ...}    │             ┌─────────────────────┐
└─────────────────┘             │        OBS          │
                                │   Scene Switcher    │
                                └─────────────────────┘
```

---

## License

MIT — free to use, modify, and distribute.
