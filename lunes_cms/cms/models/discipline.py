from django.db import models
from django.db.models.deletion import CASCADE
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey

from ..utils import get_child_count
from .static import convert_umlaute_images


class Discipline(MPTTModel):
    """
    Disciplines for training sets.
    They have a title, a description, a icon and contain training
    sets with the same topic. Inherits from `mptt.models.MPTTModel`.
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
        Group,
        on_delete=CASCADE,
        null=True,
        blank=True,
        verbose_name=_("created by"),
        related_name="discipline",
    )
    creator_is_admin = models.BooleanField(default=True, verbose_name=_("admin"))
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("parent"),
    )

    def is_valid(self):
        """Checks if a discipline itself or one of its children has at least one training set.
        If so, it is considered valid.

        :return: True if discipline is valid
        :rtype: bool
        """
        return (
            get_child_count(self) > 0
            or self.training_sets.filter(released=True).count() > 0
        )

    def get_nested_training_sets(self):
        """Returns a list of distinct training set ids that are part of this
        disipline or one of its child elements.

        :return: training set ids
        :rtype: list(int)
        """
        training_sets = []
        for child in self.get_descendants(include_self=True):
            training_sets += child.training_sets.filter(released=True).values_list(
                "id", flat=True
            )
        return set(training_sets)

    def __str__(self):
        """String representation of Discipline instance

        :return: title of discipline instance
        :rtype: str
        """
        return self.title

    class Meta:
        """
        Define user readable name of Field
        """

        verbose_name = _("discipline")
        verbose_name_plural = _("disciplines")
