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
from django.utils.html import mark_safe
from .validators import (
    validate_file_extension,
    validate_file_size,
    validate_multiple_extensions,
)
from .utils import create_ressource_path, document_to_string


class Static:
    """
    Module for static and global variables
    """

    # possible articles
    article_choices = [
        (0, "keiner"),
        (1, "der"),
        (2, "die"),
        (3, "das"),
        (4, "die (Plural)"),
    ]

    # possible word types
    word_type_choices = [("Nomen", "Substantiv"), ("Verb", "Verb"), ("Adjektiv", "Adjektiv")]

    # number of pixles used for box blurr
    blurr_radius = 30
    # maximum (width, height) of images
    img_size = (1024, 768)

    # super admin group name
    admin_group = "Lunes"

    # default group name
    default_group_name = None


def convert_umlaute_images(instance, filename):
    """Convert file name of images to handle all kind of
    characters (inluding "Umlaute" etc.).

    :param instance: instance where the current file is being attached
    :type instance: django.db.models
    :param filename: name of the file
    :type filename: str
    :return: file path of converted image
    :rtype: str
    """
    return create_ressource_path("images", filename)


def convert_umlaute_audio(instance, filename):
    """Convert file name of audios to handle all kind of
    characters (inluding "Umlaute" etc.).

    :param instance: instance where the current file is being attached
    :type instance: django.db.models
    :param filename: name of the file
    :type filename: str
    :return: file path of converted audio
    :rtype: str
    """
    return create_ressource_path("audio", filename)


class Discipline(OrderedModel):
    """
    Disciplines for training sets.
    They have a title, a description, a icon and contain training
    sets with the same topic. Inherits from `ordered_model.models.OrderedModel`.
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
        """String representation of Discipline instance

        :return: title of discipline instance
        :rtype: str
        """
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
    creation_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("creation date")
    )
    created_by = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("created by")
    )
    creator_is_admin = models.BooleanField(default=True, verbose_name=_("admin"))

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
        to mp3 format (orignal file is saved as backup).
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


class TrainingSet(OrderedModel):  # pylint: disable=R0903
    """
    Training sets are part of disciplines, have a title, a description
    an icon and relates to documents and disciplines.
    Inherits from `ordered_model.models.OrderedModel`.
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
        """String representation of TrainingSet instance

        :return: title of training set instance
        :rtype: str
        """
        return self.title

    # pylint: disable=R0903
    class Meta(OrderedModel.Meta):
        """
        Define user readable name of TrainingSet
        """

        verbose_name = _("training set")
        verbose_name_plural = _("training sets")


class DocumentImage(models.Model):
    """Contains images and its titles that can be linked to
    a document object.
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True)
    image = models.ImageField(
        upload_to=convert_umlaute_images, validators=[validate_multiple_extensions]
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="document_image"
    )
    confirmed = models.BooleanField(default=True, verbose_name="confirmed")

    def image_tag(self):
        """Image thumbnail to display a preview of a image in the editing section
        of the DocumentImage admin.

        :return: img HTML tag to display an image thumbnail
        :rtype: str
        """
        if self.image and self.image.storage.exists(self.image.name):
            if ".png" in self.image.name or ".jpg" in self.image.name:
                return mark_safe(
                    '<img src="/media/%s" width="330" height="240"/>' % (self.image)
                )
        return ""

    image_tag.short_description = ""

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
            img_cropped.thumbnail(Static.img_size)
        elif (img_cropped.width / img_cropped.height) > (Static.img_size[0] / Static.img_size[1]):
            img_cropped = img_cropped.resize((Static.img_size[0], round((Static.img_size[0] / img_cropped.width) * img_cropped.height)))
        else:
            img_cropped = img_cropped.resize((round(Static.img_size[1] / img_cropped.height) * img_cropped.width, Static.img_size[1]))

        offset = (
            ((img_blurr.width - img_cropped.width) // 2),
            ((img_blurr.height - img_cropped.height) // 2),
        )
        img_blurr.paste(img_cropped, offset)
        img_blurr.save(self.image.path)

    def __str__(self):
        """String representation of DocumentImage instance

        :return: title of document image instance
        :rtype: str
        """
        if self.name:
            return self.name
        else:
            return self.document.word

    def save(self, *args, **kwargs):
        """Overwrite djangos save function to scale images into a
        uniform size that is defined in the Static module.
        """
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
    Contains alternative words that can be linked to a document
    """

    id = models.AutoField(primary_key=True)
    alt_word = models.CharField(max_length=255, verbose_name=_("alternative word"))
    article = models.IntegerField(
        choices=Static.article_choices,
        default="",
        verbose_name=_("article"),
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="alternatives"
    )

    def __str__(self):
        """String representation of AlternativeWord instance

        :return: title of alternative word instance
        :rtype: str
        """
        return self.alt_word

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """

        verbose_name = _("alternative word")
        verbose_name_plural = _("alternative words")


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically adds a group when creating a new user
    if group name given in Static module

    :param sender: user that sends request
    :type sender: django.contrib.auth.models
    :param instance: user that eventually will be added to a new group
    :type instance: django.contrib.auth.models
    :param created: checks if User is creator
    :type created: bool
    :return: False if User is not creator and not part of Static.default_group_name
    :rtype: bool
    """
    if Static.default_group_name:
        default_group = Group.objects.filter(name=Static.default_group_name)
        if not created or not default_group:
            return False
        instance.groups.add(Group.objects.get(name=Static.default_group_name))
