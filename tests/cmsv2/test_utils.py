"""
Tests for cmsv2 utility helpers.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from unittest import mock

import pytest

from lunes_cms.cmsv2.utils import cache_busted_url, safe_temp_path


def _fake_file(url: str, name: str = "audio/Apfel.mp3") -> mock.Mock:
    file = mock.Mock()
    file.url = url
    file.name = name
    return file


def test_cache_busted_url_appends_modified_time() -> None:
    """The URL gets a ?v= query derived from the file's last-modified time."""
    file = _fake_file("/media/audio/Apfel.mp3")
    file.storage.get_modified_time.return_value = datetime.datetime(2026, 6, 10, 12, 0)

    busted = cache_busted_url(file)

    expected = int(datetime.datetime(2026, 6, 10, 12, 0).timestamp())
    assert busted == f"/media/audio/Apfel.mp3?v={expected}"


def test_cache_busted_url_changes_when_file_is_modified() -> None:
    """A regenerated file (new modification time, same URL) yields a different busted URL."""
    file = _fake_file("/media/audio/Apfel.mp3")

    file.storage.get_modified_time.return_value = datetime.datetime(2026, 6, 10, 12, 0)
    before = cache_busted_url(file)
    file.storage.get_modified_time.return_value = datetime.datetime(2026, 6, 10, 12, 5)
    after = cache_busted_url(file)

    assert before != after


def test_cache_busted_url_falls_back_when_modification_time_unavailable() -> None:
    """Storages that can't report a modification time get the plain URL."""
    file = _fake_file("/media/audio/Apfel.mp3")
    file.storage.get_modified_time.side_effect = NotImplementedError

    assert cache_busted_url(file) == "/media/audio/Apfel.mp3"


def test_safe_temp_path_resolves_a_file_in_the_directory(tmp_path: Path) -> None:
    """A plain filename resolves to that file inside the directory."""
    (tmp_path / "temp_audio_abc.mp3").write_bytes(b"audio")

    assert safe_temp_path(str(tmp_path), "temp_audio_abc.mp3") == str(
        tmp_path / "temp_audio_abc.mp3"
    )


def test_safe_temp_path_returns_none_for_a_missing_file(tmp_path: Path) -> None:
    """A filename with no file behind it resolves to None."""
    assert safe_temp_path(str(tmp_path), "never_written.mp3") is None


@pytest.mark.parametrize(
    "crafted",
    ["../outside.mp3", "../../etc/passwd", "/etc/passwd", "sub/../../outside.mp3"],
)
def test_safe_temp_path_never_resolves_outside_the_directory(
    tmp_path: Path, crafted: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A crafted request value resolves to None rather than to the outside file."""
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"not yours")
    temp_dir = tmp_path / "temp_audio"
    temp_dir.mkdir()

    with caplog.at_level(logging.WARNING):
        resolved = safe_temp_path(str(temp_dir), crafted)

    assert resolved is None, f"{crafted!r} resolved to {resolved!r}"
    assert outside.read_bytes() == b"not yours"
    assert len(caplog.records) == 1
