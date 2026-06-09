"""Shared fixtures for pure-logic module tests."""
import pytest


@pytest.fixture
def sample_mpd_xml():
    """Minimal valid SVC MPD XML for ParseMpd tests."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"
     profiles="urn:mpeg:dash:profile:svc:2011"
     minBufferTime="PT2.00S" type="static"
     mediaPresentationDuration="PT40.00S">
  <BaseURL>http://example.com/video/</BaseURL>
  <Period>
    <AdaptationSet mimeType="video/H264-SVC">
      <Representation id="0" bandwidth="500000" width="640" height="360" frameRate="24">
        <SegmentList duration="2">
          <SegmentURL media="seg0-L0.264"/>
          <SegmentURL media="seg1-L0.264"/>
        </SegmentList>
      </Representation>
      <Representation id="1" bandwidth="1500000" width="640" height="360" dependencyId="0" frameRate="24">
        <SegmentList duration="2">
          <SegmentURL media="seg0-L1.264"/>
          <SegmentURL media="seg1-L1.264"/>
        </SegmentList>
      </Representation>
      <Representation id="2" bandwidth="4000000" width="640" height="360" dependencyId="0,1" frameRate="24">
        <SegmentList duration="2">
          <SegmentURL media="seg0-L2.264"/>
          <SegmentURL media="seg1-L2.264"/>
        </SegmentList>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>'''


@pytest.fixture
def make_nal_unit():
    """Factory fixture: creates a single H.264 Annex B NAL unit."""
    def _make(nal_type, payload_size=4, ref_idc=0):
        """Create a NAL unit with start code + header + payload.

        Args:
            nal_type: NAL unit type (0-31)
            payload_size: bytes of zero-filled payload (default 4)
            ref_idc: nal_ref_idc bits (0-3, default 0)

        Returns:
            bytes: complete NAL unit with 4-byte start code
        """
        import struct
        start_code = struct.pack("BBBB", 0, 0, 0, 1)
        header_byte = (ref_idc << 5) | (nal_type & 0x1f)
        payload = b'\x00' * payload_size
        return start_code + bytes([header_byte]) + payload
    return _make


@pytest.fixture
def make_264_bitstream(make_nal_unit):
    """Factory fixture: generates a minimal H.264 Annex B bitstream."""
    def _make(nal_types):
        """Generate bitstream from a list of NAL type integers.

        Args:
            nal_types: list of int - NAL unit types in order

        Returns:
            bytes: complete Annex B bitstream
        """
        parts = [make_nal_unit(t) for t in nal_types]
        return b''.join(parts)
    return _make
