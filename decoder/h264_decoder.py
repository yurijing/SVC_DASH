"""H.264 video decoder — reads YUV frames from mplayer pipe, emits QImage."""

import os, io, subprocess, struct, ctypes, threading, time
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtGui import QImage

# Load fast C YUV→RGB converter
_lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), 'yuv2rgb.dylib'))
_lib.yuv420_to_rgb888.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
_lib.yuv420_to_rgb888.restype = None


def _yuv420_to_rgb(y, u, v, w, h):
    """Convert YUV420→RGB888 via compiled C library (<1ms per frame)."""
    rgb = (ctypes.c_ubyte * (w * h * 3))()
    _lib.yuv420_to_rgb888(y, u, v, rgb, w, h)
    return bytes(rgb)


class H264Decoder(QObject):
    """Decodes H.264 file via mplayer yuv4mpeg pipe, emits QImage frames.

    Runs in a QThread. Reads YUV4MPEG frames from mplayer's stdout pipe,
    converts to RGB QImage, and emits frame_ready signal.
    """

    frame_ready = Signal(QImage)
    finished = Signal()
    error = Signal(str)

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self._path = video_path
        self._proc = None
        self._running = False
        self._w = 0; self._h = 0; self._fps = 24
        self._frame_size = 0

    def stop(self):
        self._running = False
        if self._proc:
            try: self._proc.kill()
            except: pass

    def run(self):
        """Main decode loop — mplayer writes to temp file, Python reads."""
        self._running = True
        try:
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix='.yuv', delete=False)
            tmp_path = tmp.name; tmp.close()

            self._proc = subprocess.Popen(
                ['/Users/yrj/bin/mplayer', '-vo', f'yuv4mpeg:file={tmp_path}',
                 '-nosound', '-really-quiet', '-speed', '1', self._path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Wait for mplayer to start writing
            time.sleep(0.3)

            # Open file for reading
            f = open(tmp_path, 'rb')

            # Read YUV4MPEG2 header
            header = b''
            while self._running:
                ch = f.read(1)
                if not ch: break
                header += ch
                if ch == b'\n': break

            hdr = header.decode().strip()
            if not hdr.startswith('YUV4MPEG2'):
                self.error.emit(f"Bad header: {hdr[:50]}"); f.close(); return

            parts = hdr.split()
            for p in parts[1:]:
                if p.startswith('W'): self._w = int(p[1:])
                elif p.startswith('H'): self._h = int(p[1:])
                elif p.startswith('F'):
                    fps_str = p[1:].split(':')[0]
                    self._fps = int(fps_str) if fps_str.isdigit() else 24

            y_size = self._w * self._h
            uv_size = y_size // 4
            frame_total = 6 + y_size + uv_size * 2

            # Read frames — wait for more data when file is still growing
            while self._running:
                data = f.read(frame_total)
                if not data or len(data) < frame_total:
                    time.sleep(0.2)  # wait for more segments to arrive
                    continue

                y_data = data[6:6+y_size]
                u_data = data[6+y_size:6+y_size+uv_size]
                v_data = data[6+y_size+uv_size:6+y_size+uv_size*2]

                rgb = _yuv420_to_rgb(y_data, u_data, v_data, self._w, self._h)
                img = QImage(rgb, self._w, self._h, self._w * 3, QImage.Format_RGB888)
                self.frame_ready.emit(img.copy())

            f.close()
            os.unlink(tmp_path)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.stop()
            self.finished.emit()
