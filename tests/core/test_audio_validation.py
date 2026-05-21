"""
Tests for the audio validation logic in Document.clean() and Word.clean().
"""

from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from lunes_cms.cms.models.document import Document
from lunes_cms.cmsv2.models.word import Word


class TestDocumentClean:
    def test_passes_when_no_audio(self):
        document = Document(word="Hammer", singular_article=1)
        document.clean()

    def test_skips_validation_for_committed_audio(self):
        document = Document(word="Hammer", singular_article=1)
        document.audio = "audio/existing.mp3"

        with mock.patch(
            "lunes_cms.cms.models.document.validate_audio_upload"
        ) as mock_validate:
            document.clean()

        mock_validate.assert_not_called()

    def test_calls_validation_for_new_upload(self):
        document = Document(word="Hammer", singular_article=1)
        document.audio = ContentFile(b"fake-mp3", name="test.mp3")

        with mock.patch(
            "lunes_cms.cms.models.document.validate_audio_upload"
        ) as mock_validate:
            document.clean()

        mock_validate.assert_called_once()

    def test_raises_for_invalid_audio(self):
        document = Document(word="Hammer", singular_article=1)
        document.audio = ContentFile(b"not-audio", name="test.mp3")

        with mock.patch(
            "lunes_cms.cms.models.document.validate_audio_upload",
            side_effect=ValidationError({"audio": "Invalid audio file"}),
        ):
            with pytest.raises(ValidationError):
                document.clean()


class TestWordClean:
    def test_passes_when_no_audio(self):
        word = Word(word="Hammer", singular_article=1)
        word.clean()

    def test_calls_validation_for_new_upload(self):
        word = Word(word="Hammer", singular_article=1)
        word.audio = ContentFile(b"fake-mp3", name="test.mp3")

        with mock.patch(
            "lunes_cms.cmsv2.models.word.validate_audio_upload"
        ) as mock_validate:
            word.clean()

        mock_validate.assert_called_once()

    def test_raises_for_invalid_audio(self):
        word = Word(word="Hammer", singular_article=1)
        word.audio = ContentFile(b"not-audio", name="test.mp3")

        with mock.patch(
            "lunes_cms.cmsv2.models.word.validate_audio_upload",
            side_effect=ValidationError({"audio": "Invalid audio file"}),
        ):
            with pytest.raises(ValidationError):
                word.clean()

    @pytest.mark.django_db
    def test_skips_validation_for_unchanged_audio(self):
        word = Word.objects.create(word="Hammer", singular_article=1)
        Word.objects.filter(pk=word.pk).update(audio="audio/hammer.mp3")
        word.refresh_from_db()

        with mock.patch(
            "lunes_cms.cmsv2.models.word.validate_audio_upload"
        ) as mock_validate:
            word.clean()

        mock_validate.assert_not_called()
