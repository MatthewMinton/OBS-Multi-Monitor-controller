# 🎬 OBS Auto Scene Switcher

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey?logo=apple)
![OBS](https://img.shields.io/badge/OBS-WebSocket%20v5-purple?logo=obsstudio&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

> Automatically switches OBS scenes based on what's happening on another computer — detects PowerPoint presentation mode, active video playback, fullscreen apps, and specific application windows.

---

## ✨ Features

- 🖥️ **Cross-platform** — monitored computer can be Mac or Windows
- 📊 **PowerPoint & Keynote** — detects actual Slide Show mode, not just the app being open
- 🎥 **Video detection** — queries VLC, QuickTime, MPC-HC, mpv, and browser tabs directly
- 🔲 **Fullscreen detection** — catches any app going fullscreen
- ⚡ **Low latency** — 0.5s poll interval, only sends updates on change
- 🔌 **Dual library support** — works with both `obsws-python` and `obs-websocket-py`

---

## 🗺️ How It Works

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

## 📁 Scripts

| File | Runs On | Purpose |
|------|---------|---------|
| `obs_scene_switcher_client.py` | Mac running OBS | Receives updates, switches OBS scenes |
| `obs_monitor_server_mac.py` | Mac being monitored | Detects window/app state via AppleScript |
| `obs_monitor_server_windows.py` | Windows PC being monitored | Detects window/app state via Win32 API |

---

## 🎭 Scene Mapping

| Detected Content | OBS Scene |
|-----------------|-----------|
| 📊 PowerPoint / Keynote in presentation mode | `Live Stream Screen Powerpoint & Video` |
| 🎥 Video actively playing (VLC, QuickTime, browser, etc.) | `Powerpoint` |
| 🖥️ Everything else (default) | `Live Stream Screen` |

> ⚠️ Scene names are **case-sensitive** and must exactly match your OBS scene names. Update them in your `.env` file.

---

## 📦 Requirements

### Installing packages

A single `requirements.txt` handles all platforms. Run this once on each machine before starting:

**🪟 Windows:**
```cmd
python -m pip install -r requirements.txt
```

**🍎 Mac:**
```bash
python3 -m pip install -r requirements.txt
```

> ⚠️ Make sure you run this with the same Python version your scripts will use. If you have multiple Python versions installed, use the full path:
> ```cmd
> C:\path\to\your\python.exe -m pip install -r requirements.txt
> ```

Platform-specific packages are handled automatically:
- `pywin32` and `psutil` only install on Windows
- `obsws-python` only installs on Mac
- `python-dotenv` installs on both

---

### 🍎 OBS Mac (client)

OBS must have the WebSocket server enabled:
> OBS → Tools → WebSocket Server Settings → Enable WebSocket Server

---

### 🍎 Monitored Mac (server)

![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

No third-party libraries required — uses Python's standard library and macOS's built-in `osascript`.

> ⚠️ **Accessibility permission required:**
> System Settings → Privacy & Security → Accessibility → Add Terminal (or your Python runner)
>
> Without this, AppleScript cannot read window titles.

---

### 🪟 Monitored Windows PC (server)

No special permissions required on Windows. All dependencies are handled by `requirements.txt`.

---

## 🔐 Environment Variables & Credentials

Credentials are loaded from a `.env` file so you never hardcode passwords or IPs into the script — and never accidentally push them to GitHub.

### Setup

**1. Copy the example file and fill in your values:**
```bash
cp .env.example .env
```

**2. Edit `.env` for the Mac running OBS (client):**
```env
# OBS WebSocket credentials
OBS_PASSWORD=your_obs_websocket_password_here
OBS_HOST=localhost
OBS_PORT=4455

# IP of the computer being monitored
REMOTE_HOST=192.168.1.x
REMOTE_PORT=5555

# OBS Scene names — must match exactly (case-sensitive)
SCENE_POWERPOINT=Live Stream Screen Powerpoint & Video
SCENE_VIDEO=Powerpoint
SCENE_DEFAULT=Live Stream Screen
```

**3. Edit `.env` for the Windows monitored computer (server):**
```env
# Server port
HOST=0.0.0.0
PORT=5555
```

> ⚠️ **Never commit `.env` to GitHub.** It is already listed in `.gitignore`.
> Commit `.env.example` instead — it shows others what variables are needed without exposing your values.

### Files

| File | Committed to Git | Purpose |
|------|-----------------|---------|
| `.env` | ❌ No — in `.gitignore` | Your actual credentials |
| `.env.example` | ✅ Yes | Template showing required variables |
| `.gitignore` | ✅ Yes | Prevents `.env` from being committed |
| `requirements.txt` | ✅ Yes | Package list for all platforms |

---

## 🚀 Setup

### Step 1 — Install packages on each machine

**🪟 Windows:**
```cmd
python -m pip install -r requirements.txt
```

**🍎 Mac:**
```bash
python3 -m pip install -r requirements.txt
```

---

### Step 2 — Configure your `.env` files

Copy `.env.example` to `.env` on each machine and fill in your values (see Environment Variables section above).

---

### Step 3 — Start the server on the monitored computer

**🍎 Mac:**
```bash
python3 obs_monitor_server_mac.py
```

**🪟 Windows:**
```cmd
python obs_monitor_server_windows.py
```

When it starts, it will print its local IP address:
```
✓ Server listening on port 5555
  Set REMOTE_HOST = '192.168.1.50' in the client script
```

Update `REMOTE_HOST` in the `.env` on your OBS Mac to match.

---

### Step 4 — Start the client on the OBS Mac

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

## ⚙️ Customization

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

## 🔧 Troubleshooting

<details>
<summary><b>❌ Client can't connect to server</b></summary>

- Make sure the server script is running **before** starting the client
- Confirm the IP address in `REMOTE_HOST` in your `.env` matches the server machine
- Check that port `5555` is not blocked by a firewall
  - **Mac:** System Settings → Network → Firewall
  - **Windows:** Windows Defender Firewall → Allow an app through firewall

</details>

<details>
<summary><b>❌ OBS won't connect</b></summary>

- Make sure OBS is open and WebSocket server is enabled
- Double-check `OBS_PASSWORD` in your `.env` matches OBS exactly
- Default OBS WebSocket port is `4455`

</details>

<details>
<summary><b>❌ Scene doesn't switch</b></summary>

- Scene names are **case-sensitive** — copy them exactly from OBS into your `.env`
- Open the OBS scene list and verify the names match

</details>

<details>
<summary><b>❌ Mac server doesn't detect window titles</b></summary>

- Terminal needs Accessibility permission
- Go to: **System Settings → Privacy & Security → Accessibility → Add Terminal**
- If running via a launcher or IDE, add that app instead

</details>

<details>
<summary><b>❌ PowerPoint not detected as presenting (Windows)</b></summary>

- Make sure you're in **Slide Show** view, not Presenter View editing mode
- The script looks for a fullscreen window or a window title containing "Slide Show"
- Check Task Manager → Details to confirm the process name is `POWERPNT.EXE`

</details>

<details>
<summary><b>❌ Packages installing to wrong Python version (Windows)</b></summary>

- You may have multiple Python versions installed
- Always use `python -m pip install` instead of just `pip install`
- Or specify the full Python path:
  ```cmd
  C:\path\to\python.exe -m pip install -r requirements.txt
  ```
- In VS Code: `Ctrl + Shift + P` → Python: Select Interpreter → choose your version

</details>

---

## 🔍 How Detection Works

### 🍎 Mac (AppleScript)
- Uses `osascript` to query `System Events` for the frontmost app name and window title
- Queries **PowerPoint** directly for Slide Show state
- Queries **Keynote** directly for `playing` document state
- Queries **VLC** and **QuickTime** directly for playback state
- Falls back to window position check (`0, 0`) for fullscreen detection

### 🪟 Windows (Win32 API)
- Uses `win32gui.GetForegroundWindow()` for the active window
- Uses `psutil` to resolve PID → process name
- Enumerates all PowerPoint windows — 2+ windows = slide show is active
- Compares window rect against monitor rect for fullscreen detection
- Checks window titles for browser-based video (YouTube, Netflix, etc.)

---

## 🌐 Network Architecture

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

## 📄 License

![License](https://img.shields.io/badge/License-MIT-green)

MIT — free to use, modify, and distribute.
