import os
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.files import File
from django.db import models
from django.utils.translation import gettext_lazy as _
from pydub import AudioSegment

from .static import Static, convert_umlaute_audio, convert_umlaute_images
from ..utils import word_to_string, get_image_tag
from ..validators import (
    validate_file_extension,
    validate_file_size,
    validate_multiple_extensions,
)


class Word(models.Model):
    """
    Represents a single word with various linguistic attributes,
    including its type, grammatical features, associated audio, and images.
    """

    word_type = models.CharField(
        max_length=255,
        choices=Static.word_type_choices,
        default="",
        verbose_name=_("word type"),
    )
    word = models.CharField(max_length=255, verbose_name=_("word"))
    grammatical_gender = models.IntegerField(
        choices=Static.grammatical_genders,
        verbose_name=_("Grammatical gender"),
        blank=True,
        null=True,
    )
    singular_article = models.IntegerField(
        choices=Static.singular_article_choices,
        default="",
        verbose_name=_("singular article"),
    )
    plural = models.CharField(
        max_length=255,
        verbose_name=_("plural"),
        blank=True,
        default="",
    )
    plural_article = models.IntegerField(
        choices=Static.plural_article_choices,
        verbose_name=_("plural article"),
        blank=True,
        null=True,
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
    audio_check_status = models.CharField(
        max_length=20,
        choices=Static.check_status_choices,
        null=True,
        verbose_name=_("audio check status"),
        default="NOT_CHECKED",
    )
    audio_checked_identifier = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("audio checked identifier"),
    )
    example_sentence = models.TextField(verbose_name=_("example sentence"), blank=True)
    example_sentence_audio = models.FileField(
        upload_to=convert_umlaute_audio,
        validators=[
            validate_file_extension,
            validate_file_size,
            validate_multiple_extensions,
        ],
        blank=True,
        null=True,
        verbose_name=_("example sentence audio"),
    )
    example_sentence_check_status = models.CharField(
        max_length=20,
        choices=Static.check_status_choices,
        null=True,
        verbose_name=_("example sentence check status"),
        default="NOT_CHECKED",
    )
    creation_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("creation date")
    )
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_("modified at"))
    definition = models.TextField(
        max_length=256,
        blank=True,
        null=True,
        verbose_name=_("definition"),
    )
    additional_meaning_1 = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        verbose_name=_("additional meaning 1"),
    )
    additional_meaning_2 = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        verbose_name=_("additional meaning 2"),
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
    image = models.ImageField(
        upload_to=convert_umlaute_images, blank=True, verbose_name=_("image")
    )
    image_check_status = models.CharField(
        max_length=20,
        choices=Static.check_status_choices,
        null=True,
        verbose_name=_("image check status"),
        default="NOT_CHECKED",
    )
    v1_id = models.IntegerField(null=True, blank=True, editable=False)

    @property
    def converted(self):
        """
        Converts the uploaded audio file to MP3 format and returns it as a Django File object.
        This method is a property, so it can be accessed like an attribute.

        Returns:
            django.core.files.File or None: The converted MP3 audio file as a Django File object,
                                            or None if no audio file is associated.
        """
        if self.audio:
            super().save()
            file_path = self.audio.path
            original_extension = file_path.split(".")[-1]
            mp3_converted_file = AudioSegment.from_file(file_path, original_extension)
            new_path = file_path[:-4] + "-conv.mp3"
            mp3_converted_file.export(new_path, format="mp3", bitrate="44.1k")

            converted_audiofile = File(file=open(new_path, "rb"), name=Path(new_path))
            converted_audiofile.name = Path(new_path).name
            converted_audiofile.content_type = "audio/mpeg"
            converted_audiofile.size = os.path.getsize(new_path)
            os.remove(new_path)
            return converted_audiofile
        return None

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to handle audio conversion and
        update check statuses for audio and image files.
        """
        previous_word = Word.objects.get(pk=self.pk) if self.pk else None
        audio_updated = (not self.pk and self.audio) or (
            self.pk
            and previous_word
            and previous_word.assemble_audio_checked_identifier()
            != self.assemble_audio_checked_identifier()
        )
        image_updated = (not self.pk and self.image) or (
            self.pk and previous_word and previous_word.image != self.image
        )

        example_sentence_changed = (
            self.pk
            and previous_word
            and previous_word.example_sentence != self.example_sentence
        )
        if example_sentence_changed:
            if previous_word.example_sentence_audio:
                # Delete the old audio file from storage
                previous_word.example_sentence_audio.delete(save=False)
                self.example_sentence_audio = None
            # Reset example sentence check status when example sentence changes
            self.example_sentence_check_status = "NOT_CHECKED"

        if audio_updated:
            self.audio = self.converted
            self.audio_check_status = "NOT_CHECKED"
            self.audio_checked_identifier = self.assemble_audio_checked_identifier()

        if not self.audio:
            self.audio_check_status = None
            self.audio_checked_identifier = None

        if (
            previous_word
            and previous_word.audio_check_status != self.audio_check_status
        ):
            self.audio_checked_identifier = self.assemble_audio_checked_identifier()

        if image_updated:
            self.image_check_status = "NOT_CHECKED"

        if not self.image:
            self.image_check_status = None

        if not self.example_sentence or not self.example_sentence.strip():
            self.example_sentence_check_status = None

        super().save(*args, **kwargs)

    def assemble_audio_checked_identifier(self):
        """
        Assembles an identifier for the audio file, typically its URL,
        used to track changes for audio checking.

        Returns:
            str or None: The URL of the audio file if it exists, otherwise None.
        """
        return self.audio.url if self.audio else None

    def singular_article_for_audio_generation(self):
        """Get singular article for audio generation."""
        if self.singular_article == 0:
            return ""
        if self.singular_article == 4:
            return "die"
        for num, article in Static.singular_article_choices:
            if num == self.singular_article:
                return article
        return ""

    def image_tag(self, width=120):
        """
        Generates an HTML image tag for the word's associated image.

        Args:
            width (int, optional): The desired width of the image in pixels. Defaults to 120.

        Returns:
            str: An HTML `<img>` tag if an image exists, otherwise an empty string.
        """
        return get_image_tag(self.image, width)

    image_tag.short_description = ""

    def images_for_api(self):
        """
        Returns all images that belong to this word to be returned in the api.
        By default, this only includes the default image of this word, if it is checked.
        If the unit word relations for this word have been set, their images will be used as well.

        Returns:
            list[str]: A list of images that belong to this word.
        """
        images = [
            relation.image
            for relation in getattr(self, "unit_word_relations_of_job", [])
        ]
        if self.image_check_status == "CONFIRMED":
            images.append(self.image)

        return images

    @property
    def singular_article_as_text(self):
        """
        Returns:
            str: The singular article of this word as text
        """
        # pylint: disable=invalid-sequence-index
        return Static.singular_article_choices[self.singular_article][1]

    def __str__(self):
        """
        Returns a string representation of the Word instance, which is its actual word.

        Returns:
            str: The word itself.
        """
        return word_to_string(self)

    class Meta:
        """
        Meta options for the Word model.
        """

        verbose_name = _("Word")
        verbose_name_plural = _("Words")
