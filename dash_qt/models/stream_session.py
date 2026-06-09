"""Global state management for the DASH streaming session."""

from PySide6.QtCore import QObject, Signal


class StreamSession(QObject):
    """Central session state, shared across all widgets via signals.

    Emits state_changed(key, value) on every property update so widgets
    can subscribe and refresh independently.

    Attributes:
        mpd_url: Current MPD manifest URL.
        video_meta: Parsed MPD metadata dict (from ParseMpd.parse_mpd).
        current_segment: Index of the segment currently being downloaded.
        total_segments: Total number of segments in the video.
        downloaded_segments: Highest fully-downloaded segment index.
        current_layer: Currently selected quality layer.
        current_speed: Most recent download speed in Kbps.
        buffer_level: Number of segments currently buffered.
        strategy_name: Name of the active adaptation strategy.
        playback_state: One of "stopped", "playing", "paused".
        mpd_history: List of previously-used MPD URLs.
    """

    state_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mpd_url = ""
        self._video_meta = {}
        self._current_segment = 0
        self._total_segments = 0
        self._downloaded_segments = 0
        self._current_layer = 0
        self._current_speed = 0.0
        self._buffer_level = 0
        self._strategy_name = "fixed"
        self._playback_state = "stopped"
        self._mpd_history = []
        self._fixed_quality = 0

    def strategy_choices(self):
        """Return list of available strategy names."""
        from strategy import list_strategies
        return list_strategies()

    # --- Properties with change notification ---

    @property
    def mpd_url(self):
        return self._mpd_url

    @mpd_url.setter
    def mpd_url(self, value):
        self._mpd_url = value
        self.state_changed.emit("mpd_url", value)

    @property
    def video_meta(self):
        return self._video_meta

    @video_meta.setter
    def video_meta(self, value):
        self._video_meta = value
        self.state_changed.emit("video_meta", value)

    @property
    def current_segment(self):
        return self._current_segment

    @current_segment.setter
    def current_segment(self, value):
        self._current_segment = value
        self.state_changed.emit("current_segment", value)

    @property
    def total_segments(self):
        return self._total_segments

    @total_segments.setter
    def total_segments(self, value):
        self._total_segments = value
        self.state_changed.emit("total_segments", value)

    @property
    def downloaded_segments(self):
        return self._downloaded_segments

    @downloaded_segments.setter
    def downloaded_segments(self, value):
        self._downloaded_segments = value
        self.state_changed.emit("downloaded_segments", value)

    @property
    def current_layer(self):
        return self._current_layer

    @current_layer.setter
    def current_layer(self, value):
        self._current_layer = value
        self.state_changed.emit("current_layer", value)

    @property
    def current_speed(self):
        return self._current_speed

    @current_speed.setter
    def current_speed(self, value):
        self._current_speed = value
        self.state_changed.emit("current_speed", value)

    @property
    def buffer_level(self):
        return self._buffer_level

    @buffer_level.setter
    def buffer_level(self, value):
        self._buffer_level = value
        self.state_changed.emit("buffer_level", value)

    @property
    def strategy_name(self):
        return self._strategy_name

    @strategy_name.setter
    def strategy_name(self, value):
        self._strategy_name = value
        self.state_changed.emit("strategy_name", value)

    @property
    def playback_state(self):
        return self._playback_state

    @playback_state.setter
    def playback_state(self, value):
        self._playback_state = value
        self.state_changed.emit("playback_state", value)

    @property
    def mpd_history(self):
        return self._mpd_history

    @mpd_history.setter
    def mpd_history(self, value):
        self._mpd_history = value
        self.state_changed.emit("mpd_history", value)

    @property
    def fixed_quality(self):
        return self._fixed_quality

    @fixed_quality.setter
    def fixed_quality(self, value):
        self._fixed_quality = value
        self.state_changed.emit("fixed_quality", value)
