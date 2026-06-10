"""Tests for ParseMpd MPD XML parser."""
import pytest
from unittest.mock import patch
from xml.dom.minidom import parseString


class TestParseMpd:
    """Tests for ParseMpd.parse_mpd()."""

    @pytest.fixture
    def parser(self):
        """Create a ParseMpd instance."""
        from streaming.parse_mpd import ParseMpd
        return ParseMpd()

    def test_parse_mpd_extracts_layers_and_thresholds(self, parser, sample_mpd_xml):
        """parse_mpd returns correct layer IDs, bandwidths, and cumulative thresholds."""
        dom = parseString(sample_mpd_xml)

        with patch.object(parser, 'get_xml', return_value=dom):
            result = parser.parse_mpd("http://example.com/video/manifest.mpd")

        assert result["layer_id"] == [0, 1, 2]
        assert result["layer_bw"] == [500000.0, 1500000.0, 4000000.0]
        assert result["threshold"] == [500000.0, 2000000.0, 6000000.0]

    def test_parse_mpd_extracts_metadata(self, parser, sample_mpd_xml):
        """parse_mpd returns correct width, height, frame_rate, base_url."""
        dom = parseString(sample_mpd_xml)

        with patch.object(parser, 'get_xml', return_value=dom):
            result = parser.parse_mpd("http://example.com/video/manifest.mpd")

        assert result["width"] == "640"
        assert result["height"] == "360"
        assert result["frame_rate"] == "24"
        assert result["base_url"] == "http://example.com/video/"

    def test_parse_mpd_extracts_segments(self, parser, sample_mpd_xml):
        """parse_mpd returns correct segment count, durations, and URLs."""
        dom = parseString(sample_mpd_xml)

        with patch.object(parser, 'get_xml', return_value=dom):
            result = parser.parse_mpd("http://example.com/video/manifest.mpd")

        assert result["total_seq"] == 2
        assert result["durations"] == [2, 2, 2]  # one per SegmentList (3 Representations)
        # list_url[0] should have 3 entries (one per layer for seg 0)
        assert len(result["list_url"]) == 2
        assert len(result["list_url"][0]) == 3

    def test_parse_mpd_handles_malformed_xml(self, parser):
        """parse_mpd with invalid XML raises a parse error."""
        with patch.object(parser, 'get_xml', side_effect=Exception("parse error")):
            with pytest.raises(Exception):
                parser.parse_mpd("http://example.com/bad.mpd")
