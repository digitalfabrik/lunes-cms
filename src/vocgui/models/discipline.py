from django.db import models
from ordered_model.models import OrderedModel
from django.db.models.deletion import CASCADE
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from .static import convert_umlaute_images

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

