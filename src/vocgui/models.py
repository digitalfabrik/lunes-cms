"""
Models for the UI
"""
import os
from pathlib import Path
from .validators import validate_file_extension, validate_file_size
from django.db import models  # pylint: disable=E0401
from PIL import Image, ImageFilter
from pydub import AudioSegment
from django.core.files import File
from django.utils.translation import ugettext as _


class Static:
    """
    Module for static and global variables
    """
    article_choices = [('keiner', 'keiner'), ('der', 'der'), ('das', 'das'),
                       ('die', 'die'), ('die (Plural)', 'die (Plural)')]

    word_type_choices = [('Nomen', 'Nomen'), ('Verb', 'Verb'),
                         ('Adjektiv', 'Adjektiv')]

    blurr_radius = 30  # number of pixles used for box blurr

    img_size = (1024, 768)  # (width, height)


class Discipline(models.Model):  # pylint: disable=R0903
    """
    Disciplines for training sets. They have a title and contain training sets with the same topic.
    """
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, verbose_name=_('Bereichsname'))
    description = models.CharField(max_length=255, blank=True, verbose_name=_('Beschreibung'))
    icon = models.ImageField(upload_to='images/', blank=True, verbose_name=_('Icon'))

    def __str__(self):
        return self.title

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Field
        """
        verbose_name = _('Bereich')
        verbose_name_plural = _('Bereiche')


class Document(models.Model):  # pylint: disable=R0903
    """
    Contains words + images and relates to a training set
    """
    id = models.AutoField(primary_key=True)
    word_type = models.CharField(max_length=255, choices=Static.word_type_choices, default='',
                                 verbose_name=_('Wortart'))
    word = models.CharField(max_length=255, verbose_name=_('Wort'))
    article = models.CharField(max_length=255, choices=Static.article_choices, default='', verbose_name=_('Artikel'))
    audio = models.FileField(upload_to='audio/', validators=[validate_file_extension, validate_file_size], blank=True,
                             null=True, verbose_name=_('Audio'))
    creation_date = models.DateTimeField(auto_now_add=True)

    @property
    def converted(self, content_type='audio/mpeg'):
        super(Document, self).save()
        file_path = self.audio.path
        original_extension = file_path.split('.')[-1]
        mp3_converted_file = AudioSegment.from_file(file_path, original_extension)
        new_path = file_path[:-4] + '-conv.mp3'
        mp3_converted_file.export(new_path, format='mp3', bitrate="44.1k")

        converted_audiofile = File(
            file=open(new_path, 'rb'),
            name=Path(new_path)
        )
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

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """
        verbose_name = _('Wort')
        verbose_name_plural = _('Wörter')


class TrainingSet(models.Model):  # pylint: disable=R0903
    """
    Training sets are part of disciplines, have a title and contain words
    """
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, verbose_name=_('Modulname'))
    description = models.CharField(max_length=255, blank=True, verbose_name=_('Beschreibung'))
    discipline = models.ForeignKey(Discipline,
                                   on_delete=models.CASCADE,
                                   related_name='training_sets')
    icon = models.ImageField(upload_to='images/', blank=True, verbose_name=_('Icon'))
    documents = models.ManyToManyField(Document,
                                       related_name='training_sets')

    def __str__(self):
        return self.title + " (Bereich: " + self.discipline.title + ")"

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of TrainingSet
        """
        verbose_name = _('Modul')
        verbose_name_plural = _('Module')


class DocumentImage(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='images/')
    document = models.ForeignKey(Document,
                                 on_delete=models.CASCADE,
                                 related_name='document_image')

    def save_original_img(self):
        """
        Function to save rough image with '_original' extension
        """
        name_elements = self.image.path.split('.')
        for elem in name_elements:
            if elem != name_elements[-1]:
                new_path = elem + '_'
        new_path = new_path + 'original.' + name_elements[-1]
        img = Image.open(self.image.path)
        img.save(new_path)

    def crop_img(self):
        """
        Function that crops the image and pastes it into a blurred background
        image
        """
        img_blurr = Image.open(self.image.path)
        img_cropped = Image.open(self.image.path)

        img_blurr = img_blurr.resize((Static.img_size[0], Static.img_size[1]))
        img_blurr = img_blurr.filter(ImageFilter.BoxBlur(Static.blurr_radius))

        if img_cropped.width > Static.img_size[0] or img_cropped.height > Static.img_size[1]:
            max_size = (Static.img_size[0], Static.img_size[1])
            img_cropped.thumbnail(max_size)

        offset = (((img_blurr.width - img_cropped.width) // 2),
                  ((img_blurr.height - img_cropped.height) // 2))
        img_blurr.paste(img_cropped, offset)
        img_blurr.save(self.image.path)

    def __str__(self):
        return self.document.word + ">> Images: " + self.name

    def save(self, *args, **kwargs):
        super(DocumentImage, self).save(*args, **kwargs)
        self.save_original_img()
        self.crop_img()

    class Meta:
        """
        Define user readable name of TrainingSet
        """
        verbose_name = _('Bild')
        verbose_name_plural = _('Bilder')


class AlternativeWord(models.Model):
    """
    Contains words for a document
    """
    id = models.AutoField(primary_key=True)
    alt_word = models.CharField(max_length=255)
    article = models.CharField(max_length=255, choices=Static.article_choices, default='')
    document = models.ForeignKey(Document,
                                 on_delete=models.CASCADE,
                                 related_name='alternatives')

    def __str__(self):
        return self.alt_word

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """
        verbose_name = _('Alternatives Wort')
        verbose_name_plural = _('Alternative Wörter')
