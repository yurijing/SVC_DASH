"""Minimal PyKeyboard replacement using AppleScript on macOS.

Provides tap_key() to simulate keypress for mplayer pause/resume control.
"""
import subprocess
import platform


class PyKeyboard:
    """Cross-platform keyboard simulation for mplayer control.

    On macOS, uses osascript to send keystrokes to System Events.
    On other platforms, no-op.
    """

    def __init__(self):
        self._is_macos = platform.system() == "Darwin"

    def tap_key(self, key):
        """Simulate a key press.

        Args:
            key: Single character to tap (e.g., ' ' for space).
        """
        if self._is_macos and key == ' ':
            try:
                subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to keystroke space'],
                    check=False, capture_output=True, timeout=2)
            except Exception:
                pass
