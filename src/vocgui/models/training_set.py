from django.db import models
from ordered_model.models import OrderedModel
from django.contrib.auth.models import Group
from django.db.models.deletion import CASCADE
from django.utils.translation import ugettext_lazy as _

from .static import convert_umlaute_images
from .document import Document
from .discipline import Discipline

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

