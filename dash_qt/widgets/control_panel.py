"""Right-side control panel with all UI controls."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QSlider,
    QGroupBox, QCompleter, QSpinBox,
)
from PySide6.QtCore import Qt, Signal


class ControlPanel(QWidget):
    """Right-side panel with playback controls and live statistics.

    Layout sections:
        - Video Source (URL input + history + load button)
        - Playback Controls (play / pause / stop)
        - Segment Progress (draggable slider + segment counter)
        - Live Statistics (speed, layer, buffer status)
        - Strategy selection
    """

    # Signals emitted to MainWindow for coordination
    load_mpd = Signal(str)       # User clicked Load with URL
    play_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    seek_segment = Signal(int)   # User dragged slider to segment
    strategy_changed = Signal(str)

    def __init__(self, session, config, parent=None):
        super().__init__(parent)
        self._session = session
        self._config = config
        self._setup_ui()
        self._connect_session()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # -- Video Source --
        source_group = QGroupBox("Video Source")
        source_layout = QVBoxLayout(source_group)

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://server/video.mpd")

        # History completer
        completer = QCompleter(self._session.mpd_history)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.url_input.setCompleter(completer)

        # Restore last URL
        last_url = self._config.last_mpd_url
        if last_url:
            self.url_input.setText(last_url)

        self.load_btn = QPushButton("Load MPD")
        self.load_btn.clicked.connect(self._on_load)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.load_btn)
        source_layout.addLayout(url_layout)
        layout.addWidget(source_group)

        # -- Playback Controls --
        ctrl_group = QGroupBox("Playback")
        ctrl_layout = QVBoxLayout(ctrl_group)

        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.play_clicked.emit)

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_clicked.emit)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)

        btn_layout.addWidget(self.play_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        ctrl_layout.addLayout(btn_layout)

        # Segment slider + label
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Segment:"))
        self.segment_slider = QSlider(Qt.Horizontal)
        self.segment_slider.setRange(0, 1)
        self.segment_slider.setValue(0)
        self.segment_slider.sliderReleased.connect(self._on_slider_released)
        slider_layout.addWidget(self.segment_slider)

        self.segment_label = QLabel("0 / 0")
        slider_layout.addWidget(self.segment_label)
        ctrl_layout.addLayout(slider_layout)
        layout.addWidget(ctrl_group)

        # -- Live Statistics --
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.speed_label = QLabel("Download Rate: -- Kbps")
        stats_layout.addWidget(self.speed_label)

        self.layer_label = QLabel("Quality Layer: --")
        stats_layout.addWidget(self.layer_label)

        self.buffer_label = QLabel("Buffer: -- segments")
        self.buffer_label.setStyleSheet("color: #888;")
        stats_layout.addWidget(self.buffer_label)
        layout.addWidget(stats_group)

        # -- Strategy --
        strategy_group = QGroupBox("Adaptation Strategy")
        strategy_layout = QVBoxLayout(strategy_group)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(self._session.strategy_choices())
        self.strategy_combo.setCurrentText(self._config.default_strategy)
        self.strategy_combo.currentTextChanged.connect(self._on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)

        # Fixed quality selector (shown for 'fixed' strategy)
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Fixed Layer:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(0, 10)
        self.quality_spin.setValue(0)
        self.quality_spin.valueChanged.connect(
            lambda v: setattr(self._session, 'fixed_quality', v))
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch()
        strategy_layout.addLayout(quality_layout)
        layout.addWidget(strategy_group)

        layout.addStretch()

    def _connect_session(self):
        """React to session state changes."""
        self._session.state_changed.connect(self._on_state_changed)

    def _on_load(self):
        """User clicked Load MPD."""
        url = self.url_input.text().strip()
        if url:
            self._config.last_mpd_url = url
            self.load_mpd.emit(url)

    def _on_slider_released(self):
        """User released the segment slider."""
        target = self.segment_slider.value()
        if target <= self._session.downloaded_segments:
            self.seek_segment.emit(target)
        else:
            # Snap back -- segment not downloaded yet
            self.segment_slider.setValue(self._session.current_segment)

    def _on_strategy_changed(self, name):
        """User selected a different strategy."""
        self.strategy_changed.emit(name)

    def _on_state_changed(self, key, value):
        """Update labels when session state changes."""
        if key == "current_segment":
            self.segment_label.setText(
                "{} / {}".format(value, self._session.total_segments))
            self.segment_slider.setValue(value)
        elif key == "total_segments":
            self.segment_slider.setRange(0, value)
            self.segment_label.setText(
                "{} / {}".format(self._session.current_segment, value))
        elif key == "current_speed":
            self.speed_label.setText(
                "Download Rate: {:.0f} Kbps".format(float(value)))
        elif key == "current_layer":
            self.layer_label.setText("Quality Layer: {}".format(value))
        elif key == "buffer_level":
            color = "#4CAF50" if int(value) > 1 else "#F44336"
            self.buffer_label.setText("Buffer: {} segments".format(value))
            self.buffer_label.setStyleSheet("color: {};".format(color))
        elif key == "playback_state":
            state = str(value)
            self.play_btn.setEnabled(state != "playing")
            self.pause_btn.setEnabled(state == "playing")
            self.stop_btn.setEnabled(state != "stopped")

    def set_download_enabled(self, enabled):
        """Enable/disable the Load button."""
        self.load_btn.setEnabled(enabled)
