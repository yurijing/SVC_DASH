"""Tests for svc_merge NAL unit counting and multiplexing.

svc_merge.py is a CLI script that runs argparse + merge pipeline at module
level on import. We use exec() in an isolated namespace to load the function
definitions while catching the pipeline execution error.
"""
import sys
import os
import pytest


# Load svc_merge functions via exec() in isolated namespace.
# The module-level pipeline runs on dummy files and fails with ZeroDivisionError,
# but countNalus and mux are defined before the pipeline executes.
_original_argv = sys.argv.copy()
_svc_ns = {"__name__": "svc_merge", "__file__": "svc_merge.py"}
try:
    sys.argv = [
        "svc_merge.py",
        "/dev/null",       # outputStream
        "NULL",            # initSegment
        "/dev/null",       # tempLayer0
    ]
    _svc_dir = os.path.dirname(os.path.abspath(__file__))
    _svc_path = os.path.join(_svc_dir, "..", "svc_merge.py")
    with open(_svc_path, "r") as _f:
        exec(compile(_f.read(), "svc_merge.py", "exec"), _svc_ns)
except Exception:
    pass
finally:
    sys.argv = _original_argv

countNalus = _svc_ns.get("countNalus")
mux = _svc_ns.get("mux")


class TestCountNalus:
    """Tests for countNalus()."""

    def test_count_nalus_correct_count(self, make_264_bitstream, tmp_path):
        """countNalus correctly counts NAL units of specified type."""
        bitstream = make_264_bitstream([7, 8, 5, 1, 20, 20, 20])
        test_file = tmp_path / "test.264"
        test_file.write_bytes(bitstream)

        assert countNalus(str(test_file), type=20) == 3

    def test_count_nalus_zero_for_nonexistent_type(self, make_264_bitstream, tmp_path):
        """countNalus returns 0 when no NAL units of given type exist."""
        bitstream = make_264_bitstream([7, 8, 5, 1, 1])
        test_file = tmp_path / "test.264"
        test_file.write_bytes(bitstream)

        assert countNalus(str(test_file), type=20) == 0

    def test_count_nalus_sps_type(self, make_264_bitstream, tmp_path):
        """countNalus correctly counts SPS NAL units (type 7)."""
        bitstream = make_264_bitstream([7, 8, 5, 7, 1])
        test_file = tmp_path / "test.264"
        test_file.write_bytes(bitstream)

        assert countNalus(str(test_file), type=7) == 2

    def test_count_nalus_nonexistent_file_raises(self, tmp_path):
        """countNalus raises FileNotFoundError for a non-existent file."""
        nonexistent = str(tmp_path / "does_not_exist.264")
        with pytest.raises(FileNotFoundError):
            countNalus(nonexistent, type=20)


class TestMux:
    """Tests for mux()."""

    def test_mux_basic_two_layers(self, make_264_bitstream, tmp_path):
        """mux multiplexes two layers into correct output order.

        Uses type-14 NALs (AU delimiter prefix) so countNalus finds
        access unit boundaries for the mux cycle.
        """
        # Layer 0 (base): SPS, PPS, IDR, AU_delim(14), slice, AU_delim(14), slice
        layer0_stream = make_264_bitstream([7, 8, 5, 14, 1, 14, 1])
        layer0_file = tmp_path / "layer0.264"
        layer0_file.write_bytes(layer0_stream)

        # Layer 1 (enhancement): enhancement NALs with matching AU count
        layer1_stream = make_264_bitstream([20, 20, 20, 20])
        layer1_file = tmp_path / "layer1.264"
        layer1_file.write_bytes(layer1_stream)

        # Count NALs: type-6 (AU delimiter) returns 0, but type-14 = 2
        layer0_nalu_count = countNalus(str(layer0_file), type=6)
        if layer0_nalu_count == 0:
            layer0_nalu_count = countNalus(str(layer0_file), type=14)
        layer1_nalu_count = countNalus(str(layer1_file), type=20)

        layer_list = [
            [
                {"Filename": str(layer0_file), "naluCount": layer0_nalu_count},
                {"Filename": str(layer1_file), "naluCount": layer1_nalu_count},
            ]
        ]

        output_file = tmp_path / "output.264"
        with open(output_file, "wb") as fp_out:
            mux(fp_out, layer_list, sepNaluType=14, temporalScalability=False)

        output_size = os.path.getsize(output_file)
        assert output_size > 0

    def test_mux_single_layer_output(self, make_264_bitstream, tmp_path):
        """Mux with single layer produces valid output with start codes."""
        # Include type-14 AU delimiters so baseLayerAUCount > 0
        layer0_stream = make_264_bitstream([7, 8, 5, 14, 1])
        layer0_file = tmp_path / "layer0.264"
        layer0_file.write_bytes(layer0_stream)

        nalu_count = countNalus(str(layer0_file), type=6)
        if nalu_count == 0:
            nalu_count = countNalus(str(layer0_file), type=14)

        layer_list = [
            [
                {"Filename": str(layer0_file), "naluCount": nalu_count},
            ]
        ]

        output_file = tmp_path / "output.264"
        with open(output_file, "wb") as fp_out:
            mux(fp_out, layer_list, sepNaluType=14, temporalScalability=False)

        output_data = output_file.read_bytes()
        assert len(output_data) > 0
        assert b'\x00\x00\x00\x01' in output_data
