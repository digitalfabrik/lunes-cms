"""
Models for the UI
"""
from django.db import models  # pylint: disable=E0401
from image_cropping import ImageCropField, ImageRatioField

class Static:
    """
    Module for static and global variables
    """
    article_choices = [('der', 'der'), ('das', 'das'),
                       ('die', 'die'), ('die (Plural)', 'die (Plural)')]

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
    word = models.CharField(max_length=255)
    article = models.CharField(max_length=255, choices=Static.article_choices, default='')
    image = ImageCropField(blank=True, upload_to='images/')
    # size is "width x height"
    cropping = ImageRatioField('image', '400x400', size_warning=True)
    # image = models.FileField(upload_to='images/')
    audio = models.FileField(upload_to='audio/', blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.word

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
        return self.discipline.title + " >> " + self.title

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of TrainingSet
        """
        verbose_name = 'Modul'
        verbose_name_plural = 'Module'

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
        return self.document.word + ">> Alternative Wörter: " + self.alt_word

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """
        verbose_name = 'Alternatives Wort'
        verbose_name_plural = 'Alternative Wörter'
