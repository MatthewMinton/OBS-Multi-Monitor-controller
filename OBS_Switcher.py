"""
OBS Auto Scene Switcher - CLIENT SCRIPT
Run this on the Mac running OBS.
Switches between PowerPoint and Video scenes automatically.
Supports both obs-websocket-py and obsws-python libraries.

Credentials are loaded from a .env file — never hardcoded.
Copy .env.example to .env and fill in your values.
"""

import socket
import json
import time
import os

from dotenv import load_dotenv

load_dotenv()

# Try newer library first, fall back to older one
USING_NEW_LIB = False
try:
    import obsws_python as obs
    USING_NEW_LIB = True
    print("✓ Using obsws-python library")
except ImportError:
    try:
        from obswebsocket import obsws, requests as obs_requests
        USING_NEW_LIB = False
        print("✓ Using obs-websocket-py library")
    except ImportError:
        print("ERROR: No OBS WebSocket library found!")
        print("Please install one of these:")
        print("  pip3 install obsws-python")
        print("  OR")
        print("  pip3 install obs-websocket-py")
        exit(1)

# Configuration — loaded from .env
REMOTE_HOST  = os.getenv('REMOTE_HOST', '192.168.1.100')
REMOTE_PORT  = int(os.getenv('REMOTE_PORT', 5555))
OBS_HOST     = os.getenv('OBS_HOST', 'localhost')
OBS_PORT     = int(os.getenv('OBS_PORT', 4455))
OBS_PASSWORD = os.getenv('OBS_PASSWORD', '')

if not OBS_PASSWORD:
    print("⚠️  WARNING: OBS_PASSWORD is not set in your .env file")

# Scene names - UPDATE THESE to match your OBS scene names exactly
POWERPOINT_PRESENTATION_SCENE = os.getenv('SCENE_POWERPOINT', 'Live Stream Screen Powerpoint & Video')
VIDEO_PLAYING_SCENE            = os.getenv('SCENE_VIDEO', 'Powerpoint')
DEFAULT_SCENE                  = os.getenv('SCENE_DEFAULT', 'Live Stream Screen')


class OBSSceneSwitcher:
    def __init__(self):
        self.ws = None
        self.current_scene = None
        self.last_content_type = None

    def connect_obs(self):
        """Connect to OBS WebSocket"""
        try:
            if USING_NEW_LIB:
                self.ws = obs.ReqClient(
                    host=OBS_HOST,
                    port=OBS_PORT,
                    password=OBS_PASSWORD
                )
                response = self.ws.get_current_program_scene()
                self.current_scene = response.current_program_scene_name
            else:
                self.ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
                self.ws.connect()
                response = self.ws.call(obs_requests.GetCurrentProgramScene())
                self.current_scene = response.getSceneName()

            print("✓ Connected to OBS WebSocket")
            print(f"✓ Current scene: {self.current_scene}")
            return True

        except Exception as e:
            print(f"✗ Failed to connect to OBS: {e}")
            print("  Make sure OBS is running with WebSocket enabled")
            print("  Go to: Tools → WebSocket Server Settings in OBS")
            return False

    def switch_scene(self, scene_name):
        """Switch to a specific scene in OBS"""
        if not self.ws:
            return False

        try:
            if self.current_scene != scene_name:
                if USING_NEW_LIB:
                    self.ws.set_current_program_scene(scene_name)
                else:
                    self.ws.call(obs_requests.SetCurrentProgramScene(sceneName=scene_name))

                self.current_scene = scene_name
                print(f"→ Switched to scene: {scene_name}")
                return True
        except Exception as e:
            print(f"✗ Error switching scene: {e}")
            print(f"  Make sure scene '{scene_name}' exists in OBS")
            return False

    def determine_scene(self, monitor_info):
        """Determine which scene to use based on monitor content"""
        if "error" in monitor_info:
            print(f"✗ Monitor error: {monitor_info['error']}")
            return DEFAULT_SCENE

        content_type = monitor_info.get("content_type", "other")

        if content_type != self.last_content_type:
            self.last_content_type = content_type
            if "window_title" in monitor_info:
                if content_type == "video":
                    print(f"ℹ Video PLAYING detected - {monitor_info['window_title']}")
                elif content_type == "powerpoint_presentation":
                    print(f"ℹ PowerPoint PRESENTATION MODE detected - {monitor_info['window_title']}")
                elif content_type == "fullscreen":
                    print(f"ℹ Fullscreen detected - {monitor_info['window_title']}")
                else:
                    print(f"ℹ Default content - {monitor_info.get('window_title', '')}")
            else:
                print(f"ℹ Content type: {content_type}")

        if content_type == "powerpoint_presentation":
            return POWERPOINT_PRESENTATION_SCENE
        elif content_type == "video":
            return VIDEO_PLAYING_SCENE
        else:
            return DEFAULT_SCENE

    def connect_to_monitor(self):
        """Connect to the remote computer and start monitoring"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((REMOTE_HOST, REMOTE_PORT))
            print(f"✓ Connected to monitor server at {REMOTE_HOST}:{REMOTE_PORT}")
            print("\nMonitoring for content changes...\n")

            buffer = ""
            while True:
                data = sock.recv(4096).decode()
                if not data:
                    break

                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    try:
                        monitor_info = json.loads(line)
                        scene = self.determine_scene(monitor_info)
                        if scene:
                            self.switch_scene(scene)
                    except json.JSONDecodeError:
                        continue

        except ConnectionRefusedError:
            print(f"✗ Could not connect to {REMOTE_HOST}:{REMOTE_PORT}")
            print("  Make sure the server script is running on the remote computer")
            print("  Check that the IP address is correct")
        except KeyboardInterrupt:
            print("\n\nStopping scene switcher...")
        finally:
            sock.close()
            if self.ws:
                try:
                    if not USING_NEW_LIB:
                        self.ws.disconnect()
                except Exception:
                    pass

    def run(self):
        """Main run loop"""
        if not self.connect_obs():
            return

        print("\nStarting monitor loop...")
        self.connect_to_monitor()


if __name__ == "__main__":
    print("=" * 60)
    print("  OBS Auto Scene Switcher - PowerPoint & Video Detection")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  Remote computer: {REMOTE_HOST}:{REMOTE_PORT}")
    print(f"  OBS WebSocket: {OBS_HOST}:{OBS_PORT}")
    print(f"  PowerPoint (presentation mode) → '{POWERPOINT_PRESENTATION_SCENE}'")
    print(f"  Video (actively playing)       → '{VIDEO_PLAYING_SCENE}'")
    print(f"  Default (everything else)      → '{DEFAULT_SCENE}'")
    print()

    switcher = OBSSceneSwitcher()
    switcher.run()