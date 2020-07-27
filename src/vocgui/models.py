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
    word1 = models.CharField(max_length=255)
    word2 = models.CharField(max_length=255)
    word3 = models.CharField(max_length=255)
    image = models.FileField(upload_to='images/')
    audio = models.FileField(upload_to='audio/', blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    training_set = models.ForeignKey(TrainingSet,
                                     on_delete=models.CASCADE,
                                     related_name='documents')

    def __str__(self):
        return self.training_set.title + " >> " + self.word1 + " >> " + self.word2 + " >> " + self.word3

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """
        verbose_name = 'Wort'
        verbose_name_plural = 'Wörter'
