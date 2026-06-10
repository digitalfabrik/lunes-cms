"""
Tests for cmsv2 utility helpers.
"""

import datetime
from unittest import mock

from lunes_cms.cmsv2.utils import cache_busted_url


def _fake_file(url, name="audio/Apfel.mp3"):
    file = mock.Mock()
    file.url = url
    file.name = name
    return file


def test_cache_busted_url_appends_modified_time():
    """The URL gets a ?v= query derived from the file's last-modified time."""
    file = _fake_file("/media/audio/Apfel.mp3")
    file.storage.get_modified_time.return_value = datetime.datetime(2026, 6, 10, 12, 0)

    busted = cache_busted_url(file)

    expected = int(datetime.datetime(2026, 6, 10, 12, 0).timestamp())
    assert busted == f"/media/audio/Apfel.mp3?v={expected}"


def test_cache_busted_url_changes_when_file_is_modified():
    """A regenerated file (new mtime, same URL) yields a different busted URL."""
    file = _fake_file("/media/audio/Apfel.mp3")

    file.storage.get_modified_time.return_value = datetime.datetime(2026, 6, 10, 12, 0)
    before = cache_busted_url(file)
    file.storage.get_modified_time.return_value = datetime.datetime(2026, 6, 10, 12, 5)
    after = cache_busted_url(file)

    assert before != after


def test_cache_busted_url_falls_back_when_mtime_unavailable():
    """Storages that can't report a modification time get the plain URL."""
    file = _fake_file("/media/audio/Apfel.mp3")
    file.storage.get_modified_time.side_effect = NotImplementedError

    assert cache_busted_url(file) == "/media/audio/Apfel.mp3"
