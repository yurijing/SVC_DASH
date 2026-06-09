"""VLC media player wrapper via ctypes — embeds video in Qt widget on macOS."""

import ctypes, os, sys
from ctypes import c_void_p, c_char_p, c_int, c_long, c_ulong

_LIBVLC = None


def _load_libvlc():
    """Find and load libvlc dynamically."""
    global _LIBVLC
    if _LIBVLC:
        return _LIBVLC

    candidates = [
        "/Applications/VLC.app/Contents/MacOS/lib/libvlc.dylib",
        "/Applications/VLC.app/Contents/MacOS/lib/libvlc.5.dylib",
        "libvlc.dylib",
    ]
    for p in candidates:
        if os.path.exists(p):
            _LIBVLC = ctypes.CDLL(p)
            break
    if not _LIBVLC:
        raise RuntimeError("libvlc not found. Install VLC.app in /Applications")
    return _LIBVLC


class VLCPlayer:
    """Embedded VLC video player for Qt widgets on macOS."""

    def __init__(self, widget):
        """Create VLC player embedded in the given QWidget.

        Args:
            widget: QWidget whose winId() provides the NSView for embedding.
        """
        self._lib = _load_libvlc()
        self._setup_functions()
        self._instance = None
        self._player = None
        self._media = None
        self._widget = widget
        self._playing = False

    def _setup_functions(self):
        L = self._lib

        # Instance
        L.libvlc_new.restype = c_void_p
        L.libvlc_new.argtypes = [c_int, c_void_p]

        L.libvlc_release.restype = None
        L.libvlc_release.argtypes = [c_void_p]

        # Media
        L.libvlc_media_new_path.restype = c_void_p
        L.libvlc_media_new_path.argtypes = [c_void_p, c_char_p]

        L.libvlc_media_release.restype = None
        L.libvlc_media_release.argtypes = [c_void_p]

        # Player
        L.libvlc_media_player_new.restype = c_void_p
        L.libvlc_media_player_new.argtypes = [c_void_p]

        L.libvlc_media_player_new_from_media.restype = c_void_p
        L.libvlc_media_player_new_from_media.argtypes = [c_void_p]

        L.libvlc_media_player_release.restype = None
        L.libvlc_media_player_release.argtypes = [c_void_p]

        # Embedding (macOS NSView)
        L.libvlc_media_player_set_nsobject.restype = None
        L.libvlc_media_player_set_nsobject.argtypes = [c_void_p, c_void_p]

        # Playback control
        L.libvlc_media_player_play.restype = c_int
        L.libvlc_media_player_play.argtypes = [c_void_p]

        L.libvlc_media_player_pause.restype = None
        L.libvlc_media_player_pause.argtypes = [c_void_p]

        L.libvlc_media_player_stop.restype = None
        L.libvlc_media_player_stop.argtypes = [c_void_p]

        L.libvlc_media_player_is_playing.restype = c_int
        L.libvlc_media_player_is_playing.argtypes = [c_void_p]

        # Time/seek
        L.libvlc_media_player_get_time.restype = c_long
        L.libvlc_media_player_get_time.argtypes = [c_void_p]

        L.libvlc_media_player_set_time.restype = None
        L.libvlc_media_player_set_time.argtypes = [c_void_p, c_long]

        L.libvlc_media_player_get_length.restype = c_long
        L.libvlc_media_player_get_length.argtypes = [c_void_p]

        # Mute/volume (optional)
        L.libvlc_audio_set_mute.restype = None
        L.libvlc_audio_set_mute.argtypes = [c_void_p, c_int]

        L.libvlc_audio_set_volume.restype = c_int
        L.libvlc_audio_set_volume.argtypes = [c_void_p, c_int]

    def open(self, filepath):
        """Load a media file."""
        if not self._instance:
            self._instance = self._lib.libvlc_new(0, None)
        if self._media:
            self._lib.libvlc_media_release(self._media)
        self._media = self._lib.libvlc_media_new_path(
            self._instance, filepath.encode('utf-8'))

    def play(self):
        """Start or resume playback, embedded in the widget."""
        if self._player:
            self._lib.libvlc_media_player_play(self._player)
            self._playing = True
            return

        # Create player and embed it
        if self._media:
            self._player = self._lib.libvlc_media_player_new_from_media(
                self._media)
        else:
            self._player = self._lib.libvlc_media_player_new(self._instance)

        # Embed in Qt widget via NSView
        nsview = int(self._widget.winId())
        self._lib.libvlc_media_player_set_nsobject(self._player, nsview)

        self._lib.libvlc_media_player_play(self._player)
        self._playing = True

    def pause(self):
        """Toggle pause."""
        if self._player:
            self._lib.libvlc_media_player_pause(self._player)
            self._playing = not self._playing

    def stop(self):
        """Stop playback and release resources."""
        if self._player:
            self._lib.libvlc_media_player_stop(self._player)
            self._lib.libvlc_media_player_release(self._player)
            self._player = None
            self._playing = False
        if self._media:
            self._lib.libvlc_media_release(self._media)
            self._media = None
        if self._instance:
            self._lib.libvlc_release(self._instance)
            self._instance = None

    @property
    def is_playing(self):
        if self._player:
            return bool(self._lib.libvlc_media_player_is_playing(
                self._player))
        return False

    def get_time(self):
        """Current playback position in milliseconds."""
        if self._player:
            return self._lib.libvlc_media_player_get_time(self._player)
        return 0

    def set_time(self, ms):
        """Seek to position in milliseconds."""
        if self._player:
            self._lib.libvlc_media_player_set_time(self._player, ms)

    def get_length(self):
        """Media length in milliseconds."""
        if self._player:
            return self._lib.libvlc_media_player_get_length(self._player)
        return 0

    def seek_relative(self, seconds):
        """Seek forward/backward by seconds."""
        if self._player:
            cur = self.get_time()
            self.set_time(cur + int(seconds * 1000))

    def set_mute(self, mute):
        if self._player:
            self._lib.libvlc_audio_set_mute(self._player, 1 if mute else 0)

    def set_volume(self, vol):
        if self._player:
            self._lib.libvlc_audio_set_volume(self._player, vol)
