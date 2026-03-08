"""
OBS Auto Scene Switcher - SERVER SCRIPT (Windows)
Run this on the Windows PC being monitored.
Detects PowerPoint presentation mode, video playback, specific apps, and fullscreen.
Sends JSON updates to the OBS client script running on another computer.

Requirements:
    pip install pywin32
"""

import socket
import json
import time
import threading
import ctypes
import ctypes.wintypes

try:
    import win32gui
    import win32process
    import win32api
    import win32con
    import psutil
except ImportError:
    print("ERROR: Required packages not found.")
    print("Please install them:")
    print("  pip install pywin32 psutil")
    exit(1)

# Configuration
HOST = '0.0.0.0'       # Listen on all interfaces
PORT = 5555            # Must match REMOTE_PORT in the client script
POLL_INTERVAL = 0.5    # Seconds between checks

# --- Customize these to match what YOU want to detect ---

# Apps that should trigger the DEFAULT scene
DEFAULT_SCENE_APPS = [
    "explorer",
    "chrome",
    "firefox",
    "msedge",
    "notepad",
]

# Process names for PowerPoint / presentation apps
POWERPOINT_PROCESSES = [
    "POWERPNT.EXE",
    "Keynote",           # if using Keynote via Boot Camp
]

# Window title keywords that indicate PowerPoint is presenting
POWERPOINT_PRESENTATION_KEYWORDS = [
    "Slide Show",
    "SlideShow",
    "Presentation",
    " - PowerPoint",     # fullscreen PowerPoint often drops the title
]

# Process names for video apps
VIDEO_PROCESSES = [
    "vlc.exe",
    "wmplayer.exe",      # Windows Media Player
    "mpc-hc64.exe",      # MPC-HC
    "mpc-hc.exe",
    "mpv.exe",
    "PotPlayerMini64.exe",
    "PotPlayerMini.exe",
]

# Browser process names (for YouTube/Netflix detection via title)
BROWSER_PROCESSES = [
    "chrome.exe",
    "firefox.exe",
    "msedge.exe",
    "opera.exe",
    "brave.exe",
]

# Window title keywords that indicate browser video is playing
BROWSER_VIDEO_KEYWORDS = [
    "YouTube",
    "Netflix",
    "▶",
    "Twitch",
    "Vimeo",
    "Disney+",
    "Prime Video",
]


def get_foreground_window_info():
    """Get the process name and title of the foreground window."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "", ""

        title = win32gui.GetWindowText(hwnd)

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            process_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = ""

        return process_name, title
    except Exception:
        return "", ""


def is_window_fullscreen(hwnd=None):
    """Check if the foreground window is fullscreen."""
    try:
        if hwnd is None:
            hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return False

        # Get window rect
        rect = win32gui.GetWindowRect(hwnd)
        win_left, win_top, win_right, win_bottom = rect

        # Get monitor info for this window
        monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        monitor_info = ctypes.wintypes.RECT()

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.DWORD),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork", ctypes.wintypes.RECT),
                ("dwFlags", ctypes.wintypes.DWORD),
            ]

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(mi))

        mon_left = mi.rcMonitor.left
        mon_top = mi.rcMonitor.top
        mon_right = mi.rcMonitor.right
        mon_bottom = mi.rcMonitor.bottom

        return (win_left <= mon_left and win_top <= mon_top and
                win_right >= mon_right and win_bottom >= mon_bottom)
    except Exception:
        return False


def is_powerpoint_presenting(process_name, window_title):
    """Detect if PowerPoint is in Slide Show mode."""
    if "POWERPNT" not in process_name.upper():
        return False

    # Check window title keywords
    for kw in POWERPOINT_PRESENTATION_KEYWORDS:
        if kw.lower() in window_title.lower():
            return True

    # Check if PowerPoint window is fullscreen
    hwnd = win32gui.GetForegroundWindow()
    if is_window_fullscreen(hwnd):
        return True

    # Enumerate all PowerPoint windows — presentation mode opens a second window
    ppt_windows = []

    def enum_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                if "POWERPNT" in proc.name().upper():
                    ppt_windows.append((hwnd, title))
            except Exception:
                pass

    win32gui.EnumWindows(enum_callback, None)

    # If there are 2+ PowerPoint windows, one is likely the slide show
    if len(ppt_windows) >= 2:
        for _, title in ppt_windows:
            for kw in POWERPOINT_PRESENTATION_KEYWORDS:
                if kw.lower() in title.lower():
                    return True
        # If one of the windows is fullscreen
        for hwnd, _ in ppt_windows:
            if is_window_fullscreen(hwnd):
                return True

    return False


def is_video_playing(process_name, window_title):
    """Detect if a video player is actively playing."""
    proc_lower = process_name.lower()

    # Known video player processes
    for video_proc in VIDEO_PROCESSES:
        if video_proc.lower() in proc_lower:
            # For VLC: title changes when playing (shows filename)
            # When stopped/idle title is just "VLC media player"
            if "vlc" in proc_lower:
                return window_title.lower() not in ["vlc media player", ""]
            # For Windows Media Player
            if "wmplayer" in proc_lower:
                return " - Windows Media Player" in window_title and window_title != " - Windows Media Player"
            # For MPC-HC: title shows filename when playing
            if "mpc-hc" in proc_lower:
                return " - MPC-HC" in window_title
            # For mpv: title shows filename
            if "mpv" in proc_lower:
                return window_title not in ["mpv", ""]
            # Generic: if it's a video app and it's fullscreen
            if is_window_fullscreen():
                return True
            return True  # Assume playing if it's a known video app in foreground

    # Browser-based video
    for browser in BROWSER_PROCESSES:
        if browser.lower() in proc_lower:
            for kw in BROWSER_VIDEO_KEYWORDS:
                if kw.lower() in window_title.lower():
                    return True

    return False


def detect_content():
    """
    Main detection function. Returns a dict with:
    - content_type: "powerpoint_presentation" | "video" | "fullscreen" | "app" | "other"
    - app_name: process name of the foreground app
    - window_title: title of the foreground window
    - detail: extra info string
    """
    process_name, window_title = get_foreground_window_info()

    if not process_name:
        return {"content_type": "other", "app_name": "", "window_title": "", "detail": "No window detected"}

    # 1. PowerPoint presentation mode
    if is_powerpoint_presenting(process_name, window_title):
        return {
            "content_type": "powerpoint_presentation",
            "app_name": process_name,
            "window_title": window_title,
            "detail": "PowerPoint in Slide Show mode"
        }

    # 2. Video playback
    if is_video_playing(process_name, window_title):
        return {
            "content_type": "video",
            "app_name": process_name,
            "window_title": window_title,
            "detail": f"Video playing in {process_name}"
        }

    # 3. Fullscreen (any app)
    if is_window_fullscreen():
        return {
            "content_type": "fullscreen",
            "app_name": process_name,
            "window_title": window_title,
            "detail": f"{process_name} is fullscreen"
        }

    # 4. Watched apps
    for watched in DEFAULT_SCENE_APPS:
        if watched.lower() in process_name.lower():
            return {
                "content_type": "app",
                "app_name": process_name,
                "window_title": window_title,
                "detail": f"Watched app: {process_name}"
            }

    # 5. Default
    return {
        "content_type": "other",
        "app_name": process_name,
        "window_title": window_title,
        "detail": "No special content detected"
    }


def handle_client(conn, addr):
    """Handle a connected OBS client — stream JSON updates until disconnected."""
    print(f"✓ OBS client connected from {addr[0]}:{addr[1]}")
    last_info = None

    try:
        while True:
            info = detect_content()

            if info != last_info:
                last_info = info
                message = json.dumps(info) + "\n"
                conn.sendall(message.encode())
                print(f"→ Sent: [{info['content_type']}] {info['app_name']} - {info['window_title']}")

            time.sleep(POLL_INTERVAL)

    except (BrokenPipeError, ConnectionResetError, OSError):
        print(f"✗ Client {addr[0]} disconnected")
    except Exception as e:
        print(f"✗ Error with client {addr[0]}: {e}")
    finally:
        conn.close()


def start_server():
    """Start the TCP server and wait for OBS client connections."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "unknown"

    print("=" * 60)
    print("  OBS Monitor Server (Windows)")
    print("=" * 60)
    print(f"\n✓ Server listening on port {PORT}")
    print(f"  Set REMOTE_HOST = '{local_ip}' in the client script")
    print(f"\nDetecting:")
    print(f"  • PowerPoint Slide Show mode")
    print(f"  • Video playback (VLC, WMP, MPC-HC, mpv, browser)")
    print(f"  • Fullscreen apps")
    print(f"  • Specific apps: {', '.join(DEFAULT_SCENE_APPS)}")
    print(f"\nWaiting for OBS client to connect...\n")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n\nStopping server...")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()