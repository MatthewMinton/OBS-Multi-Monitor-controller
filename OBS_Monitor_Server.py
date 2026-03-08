"""
OBS Auto Scene Switcher - SERVER SCRIPT (Mac)
Run this on the Mac being monitored.
Detects PowerPoint presentation mode, video playback, specific apps, and fullscreen.
Sends JSON updates to the OBS client script running on another Mac.
"""

import socket
import json
import time
import subprocess
import threading

# Configuration
HOST = '0.0.0.0'       # Listen on all interfaces
PORT = 5555            # Must match REMOTE_PORT in the client script
POLL_INTERVAL = 0.5    # Seconds between checks (lower = more responsive, more CPU)

# --- Customize these to match what YOU want to detect ---

# Apps that should trigger the DEFAULT scene (just being open/focused is enough)
DEFAULT_SCENE_APPS = [
    "Finder",
    "Safari",
    "Google Chrome",
    "Notes",
]

# Apps that should trigger the POWERPOINT scene when in presentation/fullscreen mode
POWERPOINT_APPS = [
    "Microsoft PowerPoint",
    "Keynote",
]

# Apps that should trigger the VIDEO scene when actively playing
VIDEO_APPS = [
    "VLC",
    "QuickTime Player",
    "IINA",
    "YouTube",         # browser tab title match
    "Netflix",         # browser tab title match
]

# Window title keywords that suggest video is PLAYING (not paused)
VIDEO_PLAYING_KEYWORDS = [
    "▶",               # Common play indicator in titles
]

# Window title keywords that indicate PowerPoint is in presentation mode
POWERPOINT_PRESENTATION_KEYWORDS = [
    "Slide Show",
    "Presentation",
    "SlideShow",
    "Full Screen",
]


def run_applescript(script):
    """Run an AppleScript and return the output."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_frontmost_app():
    """Get the name of the frontmost (focused) application."""
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    return run_applescript(script)


def get_frontmost_window_title():
    """Get the title of the frontmost window."""
    script = '''
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        set appName to name of frontApp
        try
            set windowTitle to name of first window of frontApp
            return appName & "|" & windowTitle
        on error
            return appName & "|"
        end try
    end tell
    '''
    result = run_applescript(script)
    if "|" in result:
        parts = result.split("|", 1)
        return parts[0].strip(), parts[1].strip()
    return result.strip(), ""


def is_app_fullscreen(app_name):
    """Check if the given app has a fullscreen window."""
    script = f'''
    tell application "System Events"
        try
            set proc to first application process whose name is "{app_name}"
            set wins to windows of proc
            repeat with w in wins
                try
                    set attrs to attributes of w
                    -- Fullscreen windows typically have no title bar / are at position 0,0
                    set pos to position of w
                    set sz to size of w
                    if item 1 of pos is 0 and item 2 of pos is 0 then
                        return "true"
                    end if
                end try
            end repeat
        end try
        return "false"
    end tell
    '''
    return run_applescript(script) == "true"


def is_powerpoint_presenting():
    """Detect if Microsoft PowerPoint is in Slide Show (presentation) mode."""
    script = '''
    tell application "System Events"
        if exists (application process "Microsoft PowerPoint") then
            tell application process "Microsoft PowerPoint"
                try
                    -- Presentation mode windows have specific titles
                    set winNames to name of every window
                    repeat with wn in winNames
                        if wn contains "Slide Show" or wn contains "SlideShow" then
                            return "presenting"
                        end if
                    end repeat
                    -- Also check if it's frontmost and fullscreen
                    if frontmost is true then
                        set wins to windows
                        repeat with w in wins
                            try
                                set pos to position of w
                                if item 1 of pos is 0 and item 2 of pos is 0 then
                                    return "presenting"
                                end if
                            end try
                        end repeat
                    end if
                end try
            end tell
        end if
        return "not_presenting"
    end tell
    '''
    return run_applescript(script) == "presenting"


def is_keynote_presenting():
    """Detect if Keynote is in presentation mode."""
    script = '''
    tell application "System Events"
        if exists (application process "Keynote") then
            tell application "Keynote"
                try
                    if it is running then
                        set docList to every document
                        repeat with d in docList
                            if playing of d is true then
                                return "presenting"
                            end if
                        end repeat
                    end if
                end try
            end tell
        end if
        return "not_presenting"
    end tell
    '''
    return run_applescript(script) == "presenting"


def is_video_playing(app_name, window_title):
    """Detect if a video app is actively playing (not paused/stopped)."""

    # VLC: check if playing via AppleScript
    if app_name == "VLC":
        script = '''
        tell application "VLC"
            try
                if playing then
                    return "playing"
                end if
            end try
            return "stopped"
        end tell
        '''
        return run_applescript(script) == "playing"

    # QuickTime Player
    if app_name == "QuickTime Player":
        script = '''
        tell application "QuickTime Player"
            try
                set d to front document
                if playing of d then
                    return "playing"
                end if
            end try
            return "stopped"
        end tell
        '''
        return run_applescript(script) == "playing"

    # IINA: check window title for play indicator
    if app_name == "IINA":
        return "▶" in window_title or window_title != ""

    # Browser-based video (YouTube, Netflix, etc.) - check title keywords
    for keyword in VIDEO_PLAYING_KEYWORDS:
        if keyword in window_title:
            return True

    # Fallback: if it's a known video app and it's fullscreen, assume playing
    for video_app in VIDEO_APPS:
        if video_app.lower() in app_name.lower():
            if is_app_fullscreen(app_name):
                return True

    return False


def detect_content():
    """
    Main detection function. Returns a dict with:
    - content_type: "powerpoint_presentation" | "video" | "app" | "fullscreen" | "other"
    - app_name: name of the frontmost app
    - window_title: title of the frontmost window
    - detail: extra info string
    """
    app_name, window_title = get_frontmost_window_title()

    if not app_name:
        return {"content_type": "other", "app_name": "", "window_title": "", "detail": "No app detected"}

    # 1. Check PowerPoint / Keynote presentation mode
    if "Microsoft PowerPoint" in app_name:
        if is_powerpoint_presenting():
            return {
                "content_type": "powerpoint_presentation",
                "app_name": app_name,
                "window_title": window_title,
                "detail": "PowerPoint in Slide Show mode"
            }
        # Check window title keywords as fallback
        for kw in POWERPOINT_PRESENTATION_KEYWORDS:
            if kw.lower() in window_title.lower():
                return {
                    "content_type": "powerpoint_presentation",
                    "app_name": app_name,
                    "window_title": window_title,
                    "detail": f"PowerPoint - keyword match: {kw}"
                }

    if "Keynote" in app_name:
        if is_keynote_presenting():
            return {
                "content_type": "powerpoint_presentation",
                "app_name": app_name,
                "window_title": window_title,
                "detail": "Keynote in presentation mode"
            }

    # 2. Check video playback
    for video_app in VIDEO_APPS:
        if video_app.lower() in app_name.lower() or video_app.lower() in window_title.lower():
            if is_video_playing(app_name, window_title):
                return {
                    "content_type": "video",
                    "app_name": app_name,
                    "window_title": window_title,
                    "detail": f"Video playing in {app_name}"
                }

    # 3. Check fullscreen (any app)
    if is_app_fullscreen(app_name):
        return {
            "content_type": "fullscreen",
            "app_name": app_name,
            "window_title": window_title,
            "detail": f"{app_name} is fullscreen"
        }

    # 4. Check specific watched apps
    for watched_app in DEFAULT_SCENE_APPS:
        if watched_app.lower() in app_name.lower():
            return {
                "content_type": "app",
                "app_name": app_name,
                "window_title": window_title,
                "detail": f"Watched app: {app_name}"
            }

    # 5. Default
    return {
        "content_type": "other",
        "app_name": app_name,
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

            # Only send if something changed
            if info != last_info:
                last_info = info
                message = json.dumps(info) + "\n"
                conn.sendall(message.encode())
                print(f"→ Sent: [{info['content_type']}] {info['app_name']} - {info['window_title']}")

            time.sleep(POLL_INTERVAL)

    except (BrokenPipeError, ConnectionResetError):
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

    # Get local IP to display
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "unknown"

    print("=" * 60)
    print("  OBS Monitor Server (Mac)")
    print("=" * 60)
    print(f"\n✓ Server listening on port {PORT}")
    print(f"  Set REMOTE_HOST = '{local_ip}' in the client script")
    print(f"\nDetecting:")
    print(f"  • PowerPoint / Keynote presentation mode")
    print(f"  • Video playback (VLC, QuickTime, IINA, browser)")
    print(f"  • Fullscreen apps")
    print(f"  • Specific apps: {', '.join(DEFAULT_SCENE_APPS)}")
    print(f"\nWaiting for OBS client to connect...\n")

    try:
        while True:
            conn, addr = server.accept()
            # Handle each client in its own thread so multiple can connect
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n\nStopping server...")
    finally:
        server.close()


if __name__ == "__main__":
    # Check for Accessibility permissions (needed for AppleScript window detection)
    print("Checking permissions...")
    test = run_applescript('tell application "System Events" to get name of first application process whose frontmost is true')
    if not test:
        print("\n⚠️  WARNING: AppleScript may need Accessibility permissions.")
        print("   Go to: System Settings → Privacy & Security → Accessibility")
        print("   Add Terminal (or your Python runner) to the list.\n")
    else:
        print(f"✓ Permissions OK (frontmost app: {test})\n")

    start_server()