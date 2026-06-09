"""Video panel widget that embeds mplayer via QProcess."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal


class VideoPanel(QWidget):
    """Widget container for mplayer video rendering.

    Uses QWidget.winId() with mplayer -wid flag to render
    video directly inside the Qt widget. Supports resize
    adaptation and aspect ratio preservation.

    Attributes:
        native_width: Original video width from MPD metadata.
        native_height: Original video height from MPD metadata.
    """

    size_changed = Signal(int, int)  # width, height on resize

    def __init__(self, parent=None):
        super().__init__(parent)
        self.native_width = 640
        self.native_height = 360
        self.win_id = None
        self._mplayer_process = None
        self._setup_ui()

    def _setup_ui(self):
        """Create the native window container for mplayer."""
        from PySide6.QtWidgets import QSizePolicy

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # The container that mplayer renders into
        self.container = QWidget()
        self.container.setAttribute(Qt.WA_NativeWindow, True)
        self.container.setStyleSheet("background-color: black;")
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.container.setMinimumSize(320, 240)
        layout.addWidget(self.container, 1)  # stretch factor 1 = fill available space

        # Resolution label at the bottom
        self.resolution_label = QLabel("640x360")
        self.resolution_label.setAlignment(Qt.AlignCenter)
        self.resolution_label.setStyleSheet(
            "color: #888; background: transparent; font-size: 11px; padding: 2px;")
        layout.addWidget(self.resolution_label, 0)  # no stretch

    def get_win_id(self):
        """Return the native window ID for mplayer -wid."""
        if self.win_id is None:
            self.win_id = int(self.container.winId())
        return self.win_id

    def set_resolution(self, width, height):
        """Update the displayed native resolution."""
        self.native_width = int(width)
        self.native_height = int(height)
        self.resolution_label.setText(
            "{}x{}".format(self.native_width, self.native_height))

    def set_mplayer_process(self, process):
        """Store reference to the QProcess for resize updates."""
        self._mplayer_process = process

    def resizeEvent(self, event):
        """Notify PlaybackWorker when the video container is resized."""
        super().resizeEvent(event)
        if self.container:
            w = self.container.width()
            h = self.container.height()
            self.size_changed.emit(w, h)
