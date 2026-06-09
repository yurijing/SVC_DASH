"""Main window for the DASH Adaptive Video Player."""

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QMessageBox, QMenuBar, QMenu,
)
from PySide6.QtCore import Qt, QThread

from dash_qt.widgets.video_panel import VideoPanel
from dash_qt.widgets.control_panel import ControlPanel
from dash_qt.widgets.speed_chart import SpeedChart
from dash_qt.widgets.qtable_heatmap import QTableHeatmap
from dash_qt.widgets.log_panel import LogPanel
from dash_qt.workers.download_worker import DownloadWorker
from dash_qt.workers.playback_worker import PlaybackWorker
from dash_qt.models.stream_session import StreamSession
from dash_qt.models.app_config import AppConfig


class MainWindow(QMainWindow):
    """Top-level window wiring all four chains together."""

    def __init__(self, session, config):
        super().__init__()
        self.session = session
        self.config = config
        self._download_thread = None
        self._download_worker = None
        self._playback_thread = None
        self._playback_worker = None
        self._setup_ui()
        self._restore_geometry()

    # ── UI Setup ────────────────────────────────────────────

    def _setup_ui(self):
        """Build the complete main window layout."""
        self.setWindowTitle("DASH Adaptive Video Player")
        self.setMinimumSize(1024, 600)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("&Quit", self.close, Qt.CTRL | Qt.Key_Q)

        # Central splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Video panel
        self.video_panel = VideoPanel()
        splitter.addWidget(self.video_panel)

        # Right: Controls in a scroll area
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(350)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Control panel
        self.control_panel = ControlPanel(self.session, self.config)
        right_layout.addWidget(self.control_panel)

        # Speed chart
        self.speed_chart = SpeedChart()
        right_layout.addWidget(self.speed_chart)

        # QTable heatmap
        self.qtable_heatmap = QTableHeatmap()
        right_layout.addWidget(self.qtable_heatmap)

        # Log panel
        self.log_panel = LogPanel()
        right_layout.addWidget(self.log_panel)

        scroll.setWidget(right_widget)
        splitter.addWidget(scroll)

        splitter.setStretchFactor(0, 3)  # video: 75%
        splitter.setStretchFactor(1, 1)  # controls: 25%
        self.setCentralWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Ready — Enter MPD URL and click Load")

        # Connect signals
        self._connect_signals()

    def _connect_signals(self):
        """Wire all signals and slots together."""
        # Control panel → actions
        self.control_panel.load_mpd.connect(self._start_download)
        self.control_panel.play_clicked.connect(self._start_playback)
        self.control_panel.pause_clicked.connect(self._pause_playback)
        self.control_panel.stop_clicked.connect(self._stop_all)
        self.control_panel.seek_segment.connect(self._seek_to_segment)
        self.control_panel.strategy_changed.connect(self._on_strategy_changed)

    # ── Download ────────────────────────────────────────────

    def _start_download(self, url):
        """Create and start the download worker thread."""
        # Clean up previous run
        self._stop_download()

        self.session.mpd_url = url
        self.statusBar().showMessage("Downloading MPD: {}".format(url))
        self.log_panel.append("Connecting to: {}".format(url))
        self.speed_chart.reset()

        # Create worker and thread
        self._download_thread = QThread()
        self._download_worker = DownloadWorker(
            url,
            strategy_name=self.session.strategy_name,
            buffer_size=self.config.buffer_size,
        )
        self._download_worker._fixed_quality = self.session.fixed_quality
        self._download_worker.moveToThread(self._download_thread)

        # Wire signals
        self._download_worker.progress.connect(self._on_progress)
        self._download_worker.speed_update.connect(self._on_speed)
        self._download_worker.layer_update.connect(self._on_layer)
        self._download_worker.buffer_update.connect(self._on_buffer)
        self._download_worker.log_message.connect(self.log_panel.append)
        self._download_worker.meta_loaded.connect(self._on_meta_loaded)
        self._download_worker.playback_ready.connect(self._start_playback)
        self._download_worker.error.connect(self._on_error)
        self._download_worker.finished.connect(self._on_download_finished)

        # Thread lifecycle
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.finished.connect(self._download_worker.deleteLater)
        self._download_thread.finished.connect(self._download_thread.deleteLater)

        self._download_thread.start()

    def _stop_download(self):
        """Clean up download worker and thread."""
        if self._download_worker:
            self._download_worker.cancel()
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.quit()
            self._download_thread.wait(3000)

    # ── Download signal handlers ─────────────────────────────

    def _on_meta_loaded(self, meta):
        """MPD metadata received."""
        self.session.video_meta = meta
        self.session.total_segments = meta["total_seq"]
        self.video_panel.set_resolution(meta["width"], meta["height"])
        self.statusBar().showMessage(
            "Downloading: {}x{}, {} segments".format(
                meta["width"], meta["height"], meta["total_seq"]))
        self.control_panel.load_btn.setEnabled(False)

    def _on_progress(self, current, total):
        """Segment download progress."""
        self.session.current_segment = current
        self.session.downloaded_segments = current
        self.statusBar().showMessage(
            "Downloading segment {}/{}".format(current, total))

    def _on_speed(self, kbps):
        """Download speed update."""
        self.session.current_speed = kbps
        self.speed_chart.append(kbps)

    def _on_layer(self, layer):
        """Quality layer update."""
        self.session.current_layer = layer

    def _on_buffer(self, level):
        """Buffer level update."""
        self.session.buffer_level = level

    def _on_error(self, msg):
        """Download error — show dialog and log."""
        self.log_panel.append(msg, "ERROR")
        QMessageBox.critical(self, "Download Error", msg)
        self.control_panel.load_btn.setEnabled(True)

    def _on_download_finished(self):
        """All segments downloaded — auto-play."""
        self.statusBar().showMessage("Download complete — starting playback...")
        self.control_panel.load_btn.setEnabled(True)
        self.control_panel.play_btn.setEnabled(True)
        self._start_playback()

    # ── Playback ────────────────────────────────────────────

    def _start_playback(self, video_path=None):
        """Start video playback via PlaybackWorker.

        Args:
            video_path: Path to .264 file. Auto-derived if not given.
        """
        if not self.session.video_meta:
            return

        self._stop_playback()

        if video_path is None:
            video_name = self.session.mpd_url.split("/")[-1].replace(".mpd", "")
            video_path = "{}/out_{}.264".format(video_name, video_name)

        win_id = self.video_panel.get_win_id()
        # Get video panel screen position for window placement
        panel_geo = self.video_panel.container.mapToGlobal(
            self.video_panel.container.rect().topLeft())
        panel_size = (panel_geo.x(), panel_geo.y(),
                      self.video_panel.container.width(),
                      self.video_panel.container.height())

        self._playback_thread = QThread()
        self._playback_worker = PlaybackWorker(
            video_path, win_id=win_id, panel_geometry=panel_size)
        self._playback_worker.moveToThread(self._playback_thread)

        self._playback_worker.playback_started.connect(
            lambda s=self.session: setattr(s, 'playback_state', 'playing'))
        self._playback_worker.playback_ended.connect(self._on_playback_ended)
        self._playback_worker.error.connect(self._on_error)

        self._playback_thread.started.connect(self._playback_worker.run)
        self._playback_worker.playback_ended.connect(self._playback_thread.quit)
        self._playback_worker.error.connect(self._playback_thread.quit)
        self._playback_thread.finished.connect(self._playback_thread.deleteLater)

        self._playback_thread.start()
        self.session.playback_state = "playing"
        self.statusBar().showMessage("Playing: {}".format(video_path))

    def _pause_playback(self):
        """Stop playback (pause/resume not supported with IINA)."""
        self._stop_playback()
        self.session.playback_state = "stopped"
        self.statusBar().showMessage("Stopped")

    def _stop_playback(self):
        """Stop playback worker."""
        if self._playback_worker:
            self._playback_worker.stop()
        if self._playback_thread and self._playback_thread.isRunning():
            self._playback_thread.quit()
            self._playback_thread.wait(3000)

    def _on_playback_ended(self):
        """Playback finished naturally."""
        self.session.playback_state = "stopped"
        self.statusBar().showMessage("Playback finished")

    # ── Seek ────────────────────────────────────────────────

    def _seek_to_segment(self, segment):
        """Seek to a specific segment (re-merge + restart mplayer)."""
        self.statusBar().showMessage(
            "Seek to segment {}...".format(segment))
        self.log_panel.append(
            "Seeking to segment {}".format(segment), "WARNING")
        # Stop current playback, will restart from target segment
        self._stop_playback()
        # TODO: Phase 2 — implement rebuild from target segment

    # ── Strategy ────────────────────────────────────────────

    def _on_strategy_changed(self, name):
        """User changed the adaptation strategy."""
        self.session.strategy_name = name
        self.config.default_strategy = name
        self.log_panel.append("Strategy changed to: {}".format(name))

    # ── Lifecycle ───────────────────────────────────────────

    def _stop_all(self):
        """Stop both download and playback."""
        self._stop_playback()
        self._stop_download()
        self.session.playback_state = "stopped"
        self.statusBar().showMessage("Stopped")

    def closeEvent(self, event):
        """Save window state and clean up threads."""
        self._stop_all()
        self.config.window_geometry = self.saveGeometry()
        event.accept()

    def _restore_geometry(self):
        """Restore window geometry from saved config."""
        geom = self.config.window_geometry
        if geom:
            self.restoreGeometry(geom)
