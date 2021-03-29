"""
Models for the UI
"""
import os
from pathlib import Path

from django.db import models  # pylint: disable=E0401
from pydub import AudioSegment
from django.core.files import File


class Static:
    """
    Module for static and global variables
    """
    article_choices = [('keiner', 'keiner'), ('der', 'der'), ('das', 'das'),
                       ('die', 'die'), ('die (Plural)', 'die (Plural)')]

    word_type_choices = [('Nomen', 'Nomen'), ('Verb', 'Verb'),
                         ('Adjektiv', 'Adjektiv')]


class Discipline(models.Model):  # pylint: disable=R0903
    """
    Disciplines for training sets. They have a title and contain training sets with the same topic.
    """
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    icon = models.ImageField(upload_to='images/', blank=True)

    def __str__(self):
        return self.title

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Field
        """
        verbose_name = 'Bereich'
        verbose_name_plural = 'Bereiche'



class Document(models.Model):  # pylint: disable=R0903
    """
    Contains words + images and relates to a training set
    """
    id = models.AutoField(primary_key=True)
    word_type = models.CharField(max_length=255, choices=Static.word_type_choices, default='')
    word = models.CharField(max_length=255)
    article = models.CharField(max_length=255, choices=Static.article_choices, default='')
    audio = models.FileField(upload_to='audio/', blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)

    @property
    def converted(self,  content_type='audio/mpeg', bitrate="192k"):
        super(Document, self).save()
        file_path = self.audio.path
        original_extension = file_path.split('.')[-1]
        mp3_converted_file = AudioSegment.from_file(file_path, original_extension)
        new_path = file_path[:-3] + 'mp3'
        mp3_converted_file.export(new_path, format='mp3', bitrate="44.1k")

        converted_audiofile = File(
            file=open(new_path, 'rb'),
            name=Path(new_path)
        )
        converted_audiofile.name = Path(new_path).name
        converted_audiofile.content_type = content_type
        converted_audiofile.size = os.path.getsize(new_path)
        return converted_audiofile

    def save(self, *args, **kwarg):
        self.audio = self.converted
        super(Document, self).save(*args, **kwarg)

    def __str__(self):
        return "(" + self.article + ") " + self.word

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """
        verbose_name = 'Wort'
        verbose_name_plural = 'Wörter'


class TrainingSet(models.Model):  # pylint: disable=R0903
    """
    Training sets are part of disciplines, have a title and contain words
    """
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    discipline = models.ForeignKey(Discipline,
                                   on_delete=models.CASCADE,
                                   related_name='training_sets')
    icon = models.ImageField(upload_to='images/', blank=True)
    documents = models.ManyToManyField(Document,
                                       related_name='training_sets')

    def __str__(self):
        return self.title + " (Bereich: " + self.discipline.title + ")"

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of TrainingSet
        """
        verbose_name = 'Modul'
        verbose_name_plural = 'Module'


class DocumentImage(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='images/')
    document = models.ForeignKey(Document,
                                 on_delete=models.CASCADE,
                                 related_name='document_image')

    def __str__(self):
        return self.document.word + ">> Images: " + self.name

    class Meta:
        """
        Define user readable name of TrainingSet
        """
        verbose_name = 'Bild'
        verbose_name_plural = 'Bilder'


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
        verbose_name = 'Alternatives Wort'
        verbose_name_plural = 'Alternative Wörter'
