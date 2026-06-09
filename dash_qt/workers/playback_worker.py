"""Worker thread for video playback via system player."""

from PySide6.QtCore import QObject, Signal, QProcess


class PlaybackWorker(QObject):
    """Manages video playback lifecycle in a worker thread.

    Uses mplayer with -wid flag to embed video in a Qt widget.
    Falls back to standalone player if no win_id provided.

    Signals:
        playback_started(): Playback process has started.
        playback_ended(): Playback has finished normally.
        error(str): An error occurred during playback.
    """

    playback_started = Signal()
    playback_ended = Signal()
    error = Signal(str)

    def __init__(self, video_path, win_id=None, parent=None,
                 panel_geometry=None):
        """Initialize the playback worker.

        Args:
            video_path: Path to the H.264 video file to play.
            win_id: Native window ID for mplayer -wid embedding.
            panel_geometry: (x, y, w, h) of video panel for window positioning.
        """
        super().__init__(parent)
        self._video_path = video_path
        self._win_id = win_id
        self._panel_geometry = panel_geometry
        self._process = None

    def _find_player(self):
        """Detect the best available video player.

        Priority: mplayer > mpv > open
        When win_id is provided, only mplayer is used (for embedding).

        Returns:
            (program, args) tuple for the QProcess.
        """
        import shutil, os

        # Try mplayer first (industry standard for SVC)
        for mplayer_path in [
            os.path.expanduser("~/bin/mplayer"),
            "/usr/local/bin/mplayer",
            "mplayer",
        ]:
            if shutil.which(mplayer_path) or os.path.exists(mplayer_path):
                return mplayer_path, ["-really-quiet", self._video_path]

        # Fallback: mpv
        if shutil.which("mpv"):
            return "mpv", ["--really-quiet", self._video_path]

        # Fallback: macOS open command
        if shutil.which("open"):
            return "open", ["--wait-apps", self._video_path]

        return None, None

    def run(self):
        """Start the video player and wait for completion."""
        player, args = self._find_player()

        if player is None:
            self.error.emit(
                "No video player found. Install mplayer to ~/bin/mplayer")
            return

        self._process = QProcess()
        self._process.setProgram(player)
        self._process.setArguments(args)
        self._process.finished.connect(self._on_finished)

        self._process.start()

        if self._process.waitForStarted(10000):
            self.playback_started.emit()
            # Position mplayer window over the video panel
            self._position_window()
        else:
            self.error.emit(
                "Failed to start player: {}".format(player))
            return

        self._process.waitForFinished(-1)

    def stop(self):
        """Terminate the playback process."""
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.terminate()
            self._process.waitForFinished(3000)
            if self._process.state() != QProcess.NotRunning:
                self._process.kill()

    def _position_window(self):
        """Use AppleScript to position mplayer over the video panel area."""
        if self._panel_geometry is None:
            return
        try:
            import subprocess, time
            time.sleep(0.5)  # Wait for mplayer window to appear
            x, y, w, h = self._panel_geometry
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                tell process "mplayer"
                    set position of window 1 to {%d, %d}
                    set size of window 1 to {%d, %d}
                end tell
            end tell
            ''' % (int(x), int(y), int(w), int(h))
            subprocess.run(["osascript", "-e", script],
                          capture_output=True, timeout=3)
        except Exception:
            pass  # Window positioning is best-effort

    def _on_finished(self, exit_code, exit_status):
        """Handle player process exit."""
        if exit_status == QProcess.NormalExit:
            self.playback_ended.emit()
        elif exit_status == QProcess.CrashExit:
            self.error.emit(
                "Player crashed (exit code: {})".format(exit_code))
