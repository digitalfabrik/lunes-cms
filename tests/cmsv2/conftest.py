"""
Shared fixtures for the cmsv2 tests.
"""

from collections.abc import Generator
from unittest import mock

import pytest

from lunes_cms.cmsv2.models import Word


@pytest.fixture(autouse=True)
def bypass_audio_conversion() -> Generator[None, None, None]:
    """
    Word.save() runs ``convert_audio()`` (ffmpeg re-encodes the mp3) when an
    audio file is set. Tests feed dummy bytes through, so skip the conversion.
    """
    with mock.patch.object(Word, "convert_audio", lambda self: None):
        yield
