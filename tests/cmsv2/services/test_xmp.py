"""
Tests for the shared XMP marking packet.
"""

from lunes_cms.cmsv2.services.xmp import build_xmp_packet, DIGITAL_SOURCE_TYPE_URI


def test_packet_carries_digital_source_type() -> None:
    assert DIGITAL_SOURCE_TYPE_URI in build_xmp_packet("AI-generated audio")


def test_description_is_xml_escaped() -> None:
    packet = build_xmp_packet("Tom & <Jerry>")

    assert "Tom &amp; &lt;Jerry&gt;" in packet
    assert "<Jerry>" not in packet
