"""Worker thread for asynchronous segment downloading."""

from PySide6.QtCore import QObject, Signal, QThread


class DownloadWorker(QObject):
    """Downloads DASH segments in a background thread.

    Wraps BufferManager.download_all_segments with signal-based
    progress reporting. Runs in a QThread to keep the GUI responsive.

    Signals:
        progress(int current, int total): Segment download progress.
        speed_update(float kbps): Current download speed estimate.
        layer_update(int layer): Quality layer selected by strategy.
        buffer_update(int level): Current buffer occupancy (segments).
        log_message(str): Human-readable log message.
        meta_loaded(dict): Parsed MPD metadata (from ParseMpd).
        error(str): Fatal error message.
        finished(): All segments downloaded successfully.
    """

    progress = Signal(int, int)
    speed_update = Signal(float)
    layer_update = Signal(int)
    buffer_update = Signal(int)
    log_message = Signal(str)
    meta_loaded = Signal(dict)
    playback_ready = Signal(str)  # video_path when enough segments buffered
    error = Signal(str)
    finished = Signal()

    def __init__(self, mpd_url, strategy_name="fixed", buffer_size=10, parent=None):
        """Initialize the download worker.

        Args:
            mpd_url: Full URL of the MPD manifest file.
            strategy_name: Name of the adaptation strategy to use.
            buffer_size: Maximum buffer size in segments.
        """
        super().__init__(parent)
        self._mpd_url = mpd_url
        self._strategy_name = strategy_name
        self._buffer_size = buffer_size
        self._fixed_quality = 0
        self._cancel_requested = False

    def cancel(self):
        """Request cancellation of the download loop."""
        self._cancel_requested = True

    def run(self):
        """Execute the download pipeline in the worker thread.

        1. Parse MPD via ParseMpd
        2. Create strategy via factory
        3. Create BufferManager
        4. Loop: download segment -> update strategy -> emit signals
        5. Handle cancellation and errors
        """
        try:
            self._do_run()
        except Exception as e:
            self.error.emit("Download failed: {}".format(str(e)))

    def _do_run(self):
        """Internal download pipeline implementation."""
        from ParseMpd import ParseMpd
        from strategy.context import StrategyContext
        from BufferManager import BufferManager
        from urllib.parse import urlparse

        # 1. Parse MPD
        self.log_message.emit("Fetching MPD: {}".format(self._mpd_url))
        parser = ParseMpd()
        parse_result = parser.parse_mpd(self._mpd_url)
        self.meta_loaded.emit(parse_result)

        total_segments = parse_result["total_seq"]
        threshold = parse_result["threshold"]
        self.log_message.emit(
            "MPD parsed: {} segments, resolution {}x{}".format(
                total_segments,
                parse_result["width"],
                parse_result["height"]))

        # 2. Set up BufferManager
        base_url = parse_result["base_url"]
        cache_match = base_url.split("//")[-1].replace("/", ",").replace(":", ",")
        buffer_mgr = BufferManager(base_url, cache_match)
        buffer_mgr.buffer_length = self._buffer_size

        # 3. Create strategy context
        ctx = StrategyContext(
            name=self._strategy_name,
            thresholds=threshold,
            buffer_length=self._buffer_size,
            total_seq=total_segments,
            fixed_quality=self._fixed_quality,
        )
        self.log_message.emit("Strategy: {}".format(ctx.name))

        # 4. Download init segment
        video_name = self._mpd_url.split("/")[-1].replace(".mpd", "")
        import os
        if not os.path.exists(video_name):
            os.makedirs(video_name)

        from log_utils import timestamp
        self.log_message.emit("{}: Starting download...".format(timestamp()))

        # Download init segment
        segment_base, speed, time_interval = buffer_mgr.download_init_segment(
            video_name, parse_result["data"])

        out_name = video_name + "/" + "out_" + video_name + ".264"
        self._playback_ready_emitted = False

        # 5. Download loop
        for i in range(total_segments):
            if self._cancel_requested:
                self.log_message.emit("Download cancelled at segment {}".format(i))
                break

            # Strategy decision
            layer = ctx.select_layer(
                i, speed, buffer_mgr.buffer_list.qsize(), threshold)

            # Download
            file_list, speed, time_tmp = buffer_mgr.download_segment(
                layer, i, parse_result["list_url"])

            # Speed validation
            if time_tmp < 0.05:
                self.log_message.emit(
                    "{}: Segment {} file too small, reusing previous speed".format(
                        timestamp(), i))

            # Merge via svc_merge
            buffer_mgr.generate_h264(video_name, i, file_list, segment_base, out_name)

            # Buffer management
            cur_segment = {
                "selected_layer": layer,
                "duration": parse_result["durations"][layer],
            }
            buffer_mgr.buffer_list.put(cur_segment)
            ctx.update_state(buffer_mgr.buffer_list.qsize(), speed)

            # Emit progress signals
            self.progress.emit(i + 1, total_segments)
            self.speed_update.emit(speed / 1024 / 8)  # bps -> Kbps
            self.layer_update.emit(layer)
            self.buffer_update.emit(buffer_mgr.buffer_list.qsize())

            # Start playback after buffering enough segments
            if not self._playback_ready_emitted and i >= 0:
                self._playback_ready_emitted = True
                self.playback_ready.emit(out_name)

            self.log_message.emit(
                "{}: Segment {} done - layer {}, speed {:.0f} Kbps".format(
                    timestamp(), i, layer, speed / 1024 / 8))

        # 6. Finalize
        ctx.finalize()
        self.log_message.emit("{}: Download complete!".format(timestamp()))
        self.finished.emit()
