"""
Shared fixtures for the cmsv2 view tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_django import Settings

from lunes_cms.core import settings as core_settings


@pytest.fixture
def media_dirs(
    settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Isolate stored files and the temp directories the store views read from."""
    settings.MEDIA_ROOT = str(tmp_path)
    temp_image_dir = tmp_path / "temp_image"
    temp_audio_dir = tmp_path / "temp_audio"
    temp_image_dir.mkdir()
    temp_audio_dir.mkdir()
    monkeypatch.setattr(core_settings, "TEMP_IMAGE_DIR", str(temp_image_dir))
    monkeypatch.setattr(core_settings, "TEMP_AUDIO_DIR", str(temp_audio_dir))
    return temp_image_dir, temp_audio_dir
