"""
The XMP packet that marks generated media as AI-generated: the IPTC
``DigitalSourceType`` ``trainedAlgorithmicMedia``, shared by the image and the
audio marking.
"""

from xml.sax.saxutils import escape

DIGITAL_SOURCE_TYPE_URI = (
    "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
)


def build_xmp_packet(description: str) -> str:
    """
    Build the XMP packet carrying the IPTC ``DigitalSourceType`` marking.

    :param description: Human-readable ``dc:description`` stored beside it
    :return: The packet
    """
    return f"""<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    Iptc4xmpExt:DigitalSourceType="{DIGITAL_SOURCE_TYPE_URI}">
   <dc:description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{escape(description)}</rdf:li>
    </rdf:Alt>
   </dc:description>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
