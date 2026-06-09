"""Persistent application configuration via QSettings."""

from PySide6.QtCore import QSettings


class AppConfig:
    """Persistent configuration backed by QSettings.

    Keys stored:
        last_mpd_url: Most recently used MPD URL.
        default_strategy: Default adaptation strategy name.
        buffer_size: Buffer size in segments.
        window_geometry: Main window position and size (bytes).
        mpd_history: List of previously-used MPD URLs (JSON).
    """

    def __init__(self):
        self._settings = QSettings("DASHPlayer", "QtGUI")

    @property
    def last_mpd_url(self):
        return self._settings.value(
            "last_mpd_url",
            "http://ftp.itec.aau.at/datasets/SVCDASHDataset2015/mpd/BBB-I-360p.mpd")

    @last_mpd_url.setter
    def last_mpd_url(self, value):
        self._settings.setValue("last_mpd_url", value)

    @property
    def default_strategy(self):
        return self._settings.value("default_strategy", "fixed")

    @default_strategy.setter
    def default_strategy(self, value):
        self._settings.setValue("default_strategy", value)

    @property
    def buffer_size(self):
        return int(self._settings.value("buffer_size", 10))

    @buffer_size.setter
    def buffer_size(self, value):
        self._settings.setValue("buffer_size", int(value))

    @property
    def window_geometry(self):
        return self._settings.value("window_geometry")

    @window_geometry.setter
    def window_geometry(self, value):
        self._settings.setValue("window_geometry", value)

    @property
    def mpd_history(self):
        import json
        raw = self._settings.value("mpd_history", "[]")
        return json.loads(raw) if isinstance(raw, str) else raw

    @mpd_history.setter
    def mpd_history(self, value):
        import json
        # Keep last 20 entries
        unique = list(dict.fromkeys(value))[-20:]
        self._settings.setValue("mpd_history", json.dumps(unique))
