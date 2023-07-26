import os

from pathlib import Path
from django.core.files import File
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import ugettext_lazy as _

from pydub import AudioSegment

from ..utils import document_to_string
from ..validators import (
    validate_file_extension,
    validate_file_size,
    validate_multiple_extensions,
)
from .feedback import Feedback
from .group import Group
from .static import Static, convert_umlaute_audio


class Document(models.Model):
    """
    Contains a word type, a word, an article and an audio.
    Relates to training sets and inherits from `models.Model`.
    """

    word_type = models.CharField(
        max_length=255,
        choices=Static.word_type_choices,
        default="",
        verbose_name=_("word type"),
    )
    word = models.CharField(max_length=255, verbose_name=_("word"))
    article = models.IntegerField(
        choices=Static.article_choices,
        default="",
        verbose_name=_("article"),
    )
    audio = models.FileField(
        upload_to=convert_umlaute_audio,
        validators=[
            validate_file_extension,
            validate_file_size,
            validate_multiple_extensions,
        ],
        blank=True,
        null=True,
        verbose_name=_("audio"),
    )
    example_sentence = models.TextField(verbose_name=_("example sentence"), blank=True)
    creation_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("creation date")
    )
    created_by = models.ForeignKey(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("created by"),
        to=Group,
        on_delete=models.CASCADE,
    )
    creator_is_admin = models.BooleanField(default=True, verbose_name=_("admin"))
    feedback = GenericRelation(Feedback)

    @property
    def converted(self, content_type="audio/mpeg"):
        """
        Function that converts the uploaded audio to .mp3 and
        returns the converted file

        :param self: A handle to the :class:`models.Document`
        :type self: class: `models.Document`
        :param content_type: content type of the converted file, defaults to "audio/mpeg"
        :type request: content_type

        :return: File containing .mp3 audio
        :rtype: .mp3 File
        """
        super(Document, self).save()
        file_path = self.audio.path
        original_extension = file_path.split(".")[-1]
        mp3_converted_file = AudioSegment.from_file(file_path, original_extension)
        new_path = file_path[:-4] + "-conv.mp3"
        mp3_converted_file.export(new_path, format="mp3", bitrate="44.1k")

        converted_audiofile = File(file=open(new_path, "rb"), name=Path(new_path))
        converted_audiofile.name = Path(new_path).name
        converted_audiofile.content_type = content_type
        converted_audiofile.size = os.path.getsize(new_path)
        os.remove(new_path)
        return converted_audiofile

    def save(self, *args, **kwargs):
        """Overwrite djangos save function to convert audio files
        to mp3 format (original file is saved as backup).
        """
        if self.audio:
            self.audio = self.converted
        super(Document, self).save(*args, **kwargs)

    def __str__(self):
        """String representation of Document instance

        :return: title of document instance
        :rtype: str
        """
        return document_to_string(self)

    class Meta:
        """
        Define user readable name of Document
        """

        verbose_name = _("vocabulary")
        verbose_name_plural = _("vocabulary")
