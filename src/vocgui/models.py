"""
Models for the UI
"""
from django.db import models  # pylint: disable=E0401


class TrainingSet(models.Model):  # pylint: disable=R0903
    """
    Training sets have a title and contain words
    """
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of TrainingSet
        """
        verbose_name = 'Lektion'
        verbose_name_plural = 'Lektionen'


class Document(models.Model):  # pylint: disable=R0903
    """
    Contains words + images and relates to a training set
    """
    word = models.CharField(max_length=255, blank=True)
    image = models.FileField(upload_to='images/')
    creation_date = models.DateTimeField(auto_now_add=True)
    training_set = models.ForeignKey(TrainingSet,
                                     on_delete=models.CASCADE,
                                     related_name='documents')

    def __str__(self):
        return self.training_set.title + " >> " + self.word

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """
        verbose_name = 'Wort'
        verbose_name_plural = 'Wörter'
