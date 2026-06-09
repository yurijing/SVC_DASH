"""Left control panel — spacious layout, not cramped."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider,
    QLineEdit, QComboBox, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, QTimer
from strategy import list_strategies


class SimpleControl(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats = {"speed": 0, "bandwidth": 0, "buffer": 0,
                       "segment": 0, "total_segments": 0}
        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

    def _setup_ui(self):
        self.setMinimumWidth(340)
        self.setMaximumWidth(400)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)

        # ── URL ──
        lbl = QLabel("MPD URL")
        lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        v.addWidget(lbl)
        self.url_input = QLineEdit(
            "http://127.0.0.1:8087/dataset/mpd/BBB-I-360p.mpd")
        self.url_input.setMinimumHeight(28)
        v.addWidget(self.url_input)

        # ── Strategy ──
        lbl2 = QLabel("Strategy")
        lbl2.setStyleSheet("font-weight: bold; font-size: 13px;")
        v.addWidget(lbl2)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(list_strategies())
        self.strategy_combo.setCurrentText("fixed")
        self.strategy_combo.setMinimumHeight(28)
        v.addWidget(self.strategy_combo)

        # ── Start button ──
        self.btn_start = QPushButton("▶ Start Streaming")
        self.btn_start.setMinimumHeight(42)
        self.btn_start.setStyleSheet(
            "QPushButton { background: #007AFF; color: #fff;"
            " font-weight: bold; font-size: 15px; border-radius: 6px; }"
            "QPushButton:hover { background: #0062CC; }"
            "QPushButton:disabled { background: #999; }")
        v.addWidget(self.btn_start)

        # ── Transport ──
        row = QHBoxLayout()
        row.setSpacing(8)
        btn_style = ("QPushButton { font-size: 18px; min-height: 36px;"
                     " border: 1px solid #ccc; border-radius: 4px; }"
                     "QPushButton:hover { background: #e0e0e0; }"
                     "QPushButton:disabled { color: #ccc; }")

        self.btn_pause = QPushButton("⏯ Pause")
        self.btn_pause.setStyleSheet(btn_style)
        self.btn_pause.setEnabled(False)
        row.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setStyleSheet(btn_style)
        self.btn_stop.setEnabled(False)
        row.addWidget(self.btn_stop)
        v.addLayout(row)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #ddd;")
        v.addWidget(sep)

        # ── Stats (spacious) ──
        s = "font-size: 14px; padding: 6px 0; line-height: 1.4;"
        self.lbl_speed = QLabel("Speed\n—")
        self.lbl_speed.setStyleSheet(s)
        v.addWidget(self.lbl_speed)

        self.lbl_bw = QLabel("Bandwidth\n—")
        self.lbl_bw.setStyleSheet(s)
        v.addWidget(self.lbl_bw)

        self.lbl_buf = QLabel("Buffer\n— / 10")
        self.lbl_buf.setStyleSheet(s)
        v.addWidget(self.lbl_buf)

        self.lbl_seg = QLabel("Segment\n— / —")
        self.lbl_seg.setStyleSheet(s)
        v.addWidget(self.lbl_seg)

        v.addStretch()

        # ── Status bar ──
        # Seek slider
        v.addWidget(QLabel("Seek Segment"))
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(0)
        self.seek_slider.setEnabled(False)
        v.addWidget(self.seek_slider)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet(
            "color: #999; font-size: 12px; padding: 6px 0;")
        v.addWidget(self.lbl_status)

    def _refresh(self):
        s = self._stats
        if s["speed"]:
            spd = s["speed"]
            self.lbl_speed.setText(
                f"Speed\n{spd/1000:.1f} Mbps" if spd > 1000
                else f"Speed\n{spd:.0f} kbps")
        if s["bandwidth"]:
            bw = s["bandwidth"]
            self.lbl_bw.setText(
                f"Bandwidth\n{bw/1000:.1f} Mbps" if bw > 1000
                else f"Bandwidth\n{bw:.0f} kbps")
        self.lbl_buf.setText(f"Buffer\n{s['buffer']} / {s.get('buf_max', 10)}")
        self.lbl_seg.setText(f"Segment\n{s['segment']} / {s['total_segments']}")

    def update_stats(self, speed=None, bandwidth=None, buffer_size=None,
                     segment=None, total_segments=None, status=None):
        if speed is not None:
            self._stats["speed"] = speed
        if bandwidth is not None:
            self._stats["bandwidth"] = bandwidth
        if buffer_size is not None:
            self._stats["buffer"] = buffer_size
        if segment is not None:
            self._stats["segment"] = segment
        if total_segments is not None:
            self._stats["total_segments"] = total_segments
        if status is not None:
            self.lbl_status.setText(status)

    def set_playing(self, playing):
        self.btn_pause.setText("⏸ Pause" if playing else "▶ Play")

    def set_transport_enabled(self, enabled):
        self.btn_pause.setEnabled(enabled)
        self.btn_stop.setEnabled(enabled)
