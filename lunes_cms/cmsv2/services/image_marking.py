"""
Mark a stored AI-generated image as such. Marking an image means pasting the
visible "AI GENERATED" label into the bottom-right corner (the label) and
embedding an XMP packet whose IPTC ``DigitalSourceType`` is
``trainedAlgorithmicMedia`` (the marking).
"""

from __future__ import annotations

import os
import shutil
from functools import cache
from pathlib import Path

from PIL import Image

LABEL_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "ai_generated_label.png"
)

#: Width of the label relative to the width of the image.
LABEL_WIDTH_RATIO = 0.2

#: Distance of the label from the bottom and right edge, relative to the width
#: of the image.
LABEL_MARGIN_RATIO = 0.03

WEBP_QUALITY = 95

DIGITAL_SOURCE_TYPE_URI = (
    "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
)

XMP_PACKET = f"""<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    Iptc4xmpExt:DigitalSourceType="{DIGITAL_SOURCE_TYPE_URI}">
   <dc:description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">AI-generated image</rdf:li>
    </rdf:Alt>
   </dc:description>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>""".encode("utf-8")


def _has_marking(image: Image.Image) -> bool:
    return DIGITAL_SOURCE_TYPE_URI.encode() in image.info.get("xmp", b"")


def is_marked(path: str | Path) -> bool:
    """
    Check whether the image at ``path`` carries the machine-readable marking.
    """
    with Image.open(path) as image:
        return _has_marking(image)


@cache
def _scaled_label(width: int) -> Image.Image:
    with Image.open(LABEL_PATH) as label_file:
        label = label_file.convert("RGBA")
    return label.resize(
        (width, round(label.height * width / label.width)),
        Image.Resampling.LANCZOS,
    )


def mark_image(source_path: str | Path, target_path: str | Path) -> bool:
    """
    Paste the AI-disclosure label onto the image at ``source_path`` and embed
    the machine-readable marking, writing the result to ``target_path``. The
    source is left as it is, and its permissions carry over to the target.

    An image that already carries the marking is not written again.

    :param source_path: Path of a WebP image
    :param target_path: Path to write the marked image to
    :return: True if the target was written, False if the source is marked
    :raises OSError: If the image or the label cannot be read or written
    """
    with Image.open(source_path) as image_file:
        if _has_marking(image_file):
            return False
        has_alpha = "A" in image_file.getbands()
        image = image_file.convert("RGBA")

    width, height = image.size
    label = _scaled_label(round(width * LABEL_WIDTH_RATIO))
    margin = round(width * LABEL_MARGIN_RATIO)
    image.alpha_composite(
        label, (width - margin - label.width, height - margin - label.height)
    )

    if not has_alpha:
        image = image.convert("RGB")

    temp_path = f"{target_path}.marking"
    try:
        image.save(
            temp_path,
            format="WEBP",
            quality=WEBP_QUALITY,
            xmp=XMP_PACKET,
        )
        shutil.copymode(source_path, temp_path)
        os.replace(temp_path, target_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return True
