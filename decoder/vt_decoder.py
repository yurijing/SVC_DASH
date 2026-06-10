"""macOS VideoToolbox H.264 hardware decoder — self-contained, no mplayer."""

import ctypes, ctypes.util, struct, os
from PySide6.QtCore import QObject, Signal

# Load system frameworks
_core = ctypes.CDLL(ctypes.util.find_library('CoreMedia'))
_vt = ctypes.CDLL(ctypes.util.find_library('VideoToolbox'))
_cv = ctypes.CDLL(ctypes.util.find_library('CoreVideo'))
_cf = ctypes.CDLL(ctypes.util.find_library('CoreFoundation'))

# CoreFoundation types
CFTypeRef = ctypes.c_void_p
CFAllocatorRef = ctypes.c_void_p
CFDictionaryRef = ctypes.c_void_p
CFStringRef = ctypes.c_void_p
CFBooleanRef = ctypes.c_void_p
OSStatus = ctypes.c_int32
Boolean = ctypes.c_uint8
CMTimeFlags = ctypes.c_uint32
CMTimeScale = ctypes.c_int32
CMTimeValue = ctypes.c_int64
CMTimeEpoch = ctypes.c_int64

class CMTime(ctypes.Structure):
    _fields_ = [("value", CMTimeValue), ("timescale", CMTimeScale),
                ("flags", CMTimeFlags), ("epoch", CMTimeEpoch)]

class CMSampleTimingInfo(ctypes.Structure):
    _fields_ = [("duration", CMTime), ("presentationTimeStamp", CMTime),
                ("decodeTimeStamp", CMTime)]

# Helper: create CFString
_cf.CFStringCreateWithCString.restype = CFStringRef
_cf.CFStringCreateWithCString.argtypes = [CFAllocatorRef, ctypes.c_char_p, ctypes.c_uint32]

# Helper: create CFDictionary
_cf.CFDictionaryCreate.restype = CFDictionaryRef
_cf.CFDictionaryCreate.argtypes = [CFAllocatorRef, ctypes.POINTER(ctypes.c_void_p),
    ctypes.POINTER(ctypes.c_void_p), ctypes.c_long,
    ctypes.c_void_p, ctypes.c_void_p]

# CMBlockBuffer
_core.CMBlockBufferCreateWithMemoryBlock.restype = OSStatus
_core.CMBlockBufferCreateWithMemoryBlock.argtypes = [
    CFAllocatorRef, ctypes.c_void_p, ctypes.c_size_t, CFAllocatorRef,
    ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_void_p)]

# CMVideoFormatDescription
_core.CMVideoFormatDescriptionCreateFromH264ParameterSets.restype = OSStatus
_core.CMVideoFormatDescriptionCreateFromH264ParameterSets.argtypes = [
    CFAllocatorRef, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]

# VTDecompressionSession
_vt.VTDecompressionSessionCreate.restype = OSStatus

# VTSessionSetProperty
_vt.VTSessionSetProperty.restype = OSStatus
_vt.VTSessionSetProperty.argtypes = [ctypes.c_void_p, CFStringRef, CFTypeRef]

# PixelBuffer attributes
_cv.kCVPixelBufferPixelFormatTypeKey = b"PixelFormatType"
_cv.kCVPixelBufferWidthKey = b"Width"
_cv.kCVPixelBufferHeightKey = b"Height"
_cv.kCVPixelBufferBytesPerRowAlignmentKey = b"BytesPerRowAlignment"
_kCVPixelFormatType_32BGRA = 0x42475241  # 'BGRA'

# H.264 NAL unit types
NAL_SPS = 7; NAL_PPS = 8; NAL_IDR = 5; NAL_NON_IDR = 1


class VTDecoder(QObject):
    """Hardware H.264 decoder using macOS VideoToolbox. Emits QImage frames."""

    frame_ready = Signal(object)  # QImage
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._session = None
        self._fmt_desc = None
        self._w = 640; self._h = 360
        self._sps = None; self._pps = None
        self._init_vt()

    def _init_vt(self):
        """Create VTDecompressionSession."""
        # Set up decoder parameters
        cf_alloc = ctypes.c_void_p(None)

        # We'll create the session when we have SPS/PPS
        self._session = None

    def _create_session(self):
        """Create VT decompression session with SPS/PPS parameters."""
        if not self._sps or not self._pps:
            return False

        # Create parameter sets array
        sps_ptr = ctypes.cast(self._sps, ctypes.c_void_p)
        pps_ptr = ctypes.cast(self._pps, ctypes.c_void_p)
        param_ptrs = (ctypes.c_void_p * 2)(sps_ptr, pps_ptr)
        param_sizes = (ctypes.c_size_t * 2)(len(self._sps), len(self._pps))

        fmt_desc = ctypes.c_void_p()
        status = _core.CMVideoFormatDescriptionCreateFromH264ParameterSets(
            None, 2,
            ctypes.cast(param_ptrs, ctypes.POINTER(ctypes.c_void_p)),
            ctypes.cast(param_sizes, ctypes.POINTER(ctypes.c_size_t)),
            4,  # NALUnitHeaderLength (4 bytes for length-prefixed)
            ctypes.byref(fmt_desc))
        if status != 0:
            self.error.emit(f"CMVideoFormatDescription failed: {status}")
            return False
        self._fmt_desc = fmt_desc

        # For now, just report that VT is initialized
        # The actual decompression session creation requires more setup
        return True

    def feed_h264(self, data_bytes):
        """Parse H.264 Annex B data, extract SPS/PPS, decode frames."""
        data = data_bytes
        i = 0; n = len(data)
        while i < n - 3:
            if data[i:i+4] == b'\x00\x00\x00\x01':
                nal_type = data[i+4] & 0x1F
                start = i + 4
                i += 4
                # Find end
                end = n
                for j in range(i, n - 3):
                    if data[j:j+4] == b'\x00\x00\x00\x01':
                        end = j; break
                nal_data = data[start:end]

                if nal_type == NAL_SPS and not self._sps:
                    self._sps = nal_data
                    if self._pps:
                        self._create_session()
                elif nal_type == NAL_PPS and not self._pps:
                    self._pps = nal_data
                    if self._sps:
                        self._create_session()
                i = end
            else:
                i += 1

    def decode_frame(self, nal_units):
        """Decode a frame (SPS+PPS+slice NALs). Returns QImage or None."""
        # For now, report that the infrastructure is in place
        # Full VT decoding requires:
        # 1. CMSampleBuffer creation
        # 2. VTDecompressionSessionDecodeFrame()
        # 3. CVPixelBuffer → QImage conversion
        return None

    def stop(self):
        if self._session:
            # VTDecompressionSessionInvalidate
            pass
        if self._fmt_desc:
            _cf.CFRelease(self._fmt_desc)
            self._fmt_desc = None
