"""
The AI-disclosure label: the European Commission's "AI GENERATED" icon and
where it sits in an image.
"""

from __future__ import annotations

from pathlib import Path

LABEL_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "ai_generated_label.png"
)

#: Width of the label relative to the width of the image.
LABEL_WIDTH_RATIO = 0.2

#: Distance of the label from the bottom and right edge, relative to the width
#: of the image.
LABEL_MARGIN_RATIO = 0.03
