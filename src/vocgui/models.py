"""
Models for the UI
"""
import os
from pathlib import Path
from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.deletion import CASCADE
from ordered_model.models import OrderedModel
from PIL import Image, ImageFilter
from pydub import AudioSegment
from django.core.files import File
from django.utils.translation import ugettext_lazy as _
from .validators import (
    validate_file_extension,
    validate_file_size,
    validate_multiple_extensions,
)


class Static:
    """
    Module for static and global variables
    """

    # possible articles
    article_choices = [
        ("keiner", "keiner"),
        ("der", "der"),
        ("das", "das"),
        ("die", "die"),
        ("die (Plural)", "die (Plural)"),
    ]

    # possible word types
    word_type_choices = [("Nomen", "Nomen"), ("Verb", "Verb"), ("Adjektiv", "Adjektiv")]

    # number of pixles used for box blurr
    blurr_radius = 30
    # maximum (width, height) of images
    img_size = (1024, 768)

    # letters that should be converted
    replace_dict = {
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }

    # super admin group name
    admin_group = "Lunes"

    # default group name
    default_group_name = None


def convert_umlaute_images(instance, filename):
    for i, j in Static.replace_dict.items():
        filename = filename.replace(i, j)
    return os.path.join("images/", filename)


def convert_umlaute_audio(instance, filename):
    for i, j in Static.replace_dict.items():
        filename = filename.replace(i, j)
    return os.path.join("audio/", filename)


class Discipline(OrderedModel):
    """
    Disciplines for training sets.
    They have a title, a description, a icon and contain training
    sets with the same topic. Inherits from `models.Model`.
    """

    id = models.AutoField(primary_key=True)
    released = models.BooleanField(default=False, verbose_name=_("released"))
    title = models.CharField(max_length=255, verbose_name=_("discipline"))
    description = models.CharField(
        max_length=255, blank=True, verbose_name=_("description")
    )
    icon = models.ImageField(
        upload_to=convert_umlaute_images, blank=True, verbose_name=_("icon")
    )
    created_by = models.ForeignKey(
        Group, on_delete=CASCADE, null=True, blank=True, verbose_name=_("created by")
    )
    creator_is_admin = models.BooleanField(default=True, verbose_name=_("admin"))

    def __str__(self):
        return self.title

    class Meta(OrderedModel.Meta):
        """
        Define user readable name of Field
        """

        verbose_name = _("discipline")
        verbose_name_plural = _("disciplines")


class Document(models.Model):
    """
    Contains a word type, a word, an article and an audio.
    Relates to training sets and inherits from `models.Model`.
    """

    id = models.AutoField(primary_key=True)
    word_type = models.CharField(
        max_length=255,
        choices=Static.word_type_choices,
        default="",
        verbose_name=_("word type"),
    )
    word = models.CharField(max_length=255, verbose_name=_("word"))
    article = models.CharField(
        max_length=255,
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
    creation_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("creation date")
    )
    created_by = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("created by")
    )
    creator_is_admin = models.BooleanField(default=True, verbose_name=_("admin"))
    plural_article = models.BooleanField(default=False)

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

    def save(self, *args, **kwarg):
        if self.audio:
            self.audio = self.converted
        super(Document, self).save(*args, **kwarg)

    def __str__(self):
        return "(" + self.article + ") " + self.word

    class Meta:
        """
        Define user readable name of Document
        """

        verbose_name = _("vocabulary")
        verbose_name_plural = _("vocabulary")


class TrainingSet(OrderedModel):  # pylint: disable=R0903
    """
    Training sets are part of disciplines, have a title, a description
    an icon and relates to documents and disciplines.
    Inherits from `models.Model`.
    """

    id = models.AutoField(primary_key=True)
    released = models.BooleanField(default=False, verbose_name=_("released"))
    title = models.CharField(max_length=255, verbose_name=_("training set"))
    description = models.CharField(
        max_length=255, blank=True, verbose_name=_("description")
    )
    icon = models.ImageField(
        upload_to=convert_umlaute_images, blank=True, verbose_name=_("icon")
    )
    documents = models.ManyToManyField(Document, related_name="training_sets")
    discipline = models.ManyToManyField(Discipline, related_name="training_sets")
    created_by = models.ForeignKey(
        Group, on_delete=CASCADE, null=True, blank=True, verbose_name=_("created by")
    )
    creator_is_admin = models.BooleanField(default=True, verbose_name=_("admin"))

    def __str__(self):
        return self.title

    # pylint: disable=R0903
    class Meta(OrderedModel.Meta):
        """
        Define user readable name of TrainingSet
        """

        verbose_name = _("training set")
        verbose_name_plural = _("training sets")


class DocumentImage(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True)
    image = models.ImageField(
        upload_to=convert_umlaute_images, validators=[validate_multiple_extensions]
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="document_image"
    )

    def save_original_img(self):
        """
        Function to save rough image with '_original' extension

        :param self: A handle to the :class:`model.DocumentImage`
        :type self: class: `model.DocumentImage`

        :return: None
        :rtype: None
        """
        name_elements = self.image.path.split(".")
        for elem in name_elements:
            if elem != name_elements[-1]:
                new_path = elem + "_"
        new_path = new_path + "original." + name_elements[-1]
        img = Image.open(self.image.path)
        img.save(new_path)

    def crop_img(self):
        """
        Function that crops the image and pastes it into a blurred background
        image

        :param self: A handle to the :class:`DocumentImage`
        :type self: class: `DocumentImage`

        :return: None
        :rtype: None
        """
        img_blurr = Image.open(self.image.path)
        img_cropped = Image.open(self.image.path)

        img_blurr = img_blurr.resize((Static.img_size[0], Static.img_size[1]))
        img_blurr = img_blurr.filter(ImageFilter.BoxBlur(Static.blurr_radius))

        if (
            img_cropped.width > Static.img_size[0]
            or img_cropped.height > Static.img_size[1]
        ):
            max_size = (Static.img_size[0], Static.img_size[1])
            img_cropped.thumbnail(max_size)

        offset = (
            ((img_blurr.width - img_cropped.width) // 2),
            ((img_blurr.height - img_cropped.height) // 2),
        )
        img_blurr.paste(img_cropped, offset)
        img_blurr.save(self.image.path)

    def __str__(self):
        if self.name:
            return self.name
        else:
            return self.document.word

    def save(self, *args, **kwargs):
        super(DocumentImage, self).save(*args, **kwargs)
        self.save_original_img()
        self.crop_img()

    class Meta:
        """
        Define user readable name of TrainingSet
        """

        verbose_name = _("image")
        verbose_name_plural = _("images")


class AlternativeWord(models.Model):
    """
    Contains words for a document
    """

    id = models.AutoField(primary_key=True)
    alt_word = models.CharField(max_length=255, verbose_name=_("alternative word"))
    article = models.CharField(
        max_length=255,
        choices=Static.article_choices,
        default="",
        verbose_name=_("article"),
    )
    plural_article = models.BooleanField(default=False)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="alternatives"
    )

    def __str__(self):
        return self.alt_word

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """

        verbose_name = _("alternative word")
        verbose_name_plural = _("alternative words")


# automatically adds a group when creating a new user if group name given in Static module
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if Static.default_group_name and created:
        instance.groups.add(Group.objects.get(name=Static.default_group_name))
