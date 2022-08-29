from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db.models.deletion import CASCADE
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html

from ..utils import get_image_tag
from .feedback import Feedback
from .static import convert_umlaute_images
from .document import Document
from .discipline import Discipline


class TrainingSet(MPTTModel):  # pylint: disable=R0903
    """
    Training sets are part of disciplines, have a title, a description
    an icon and relates to documents and disciplines.
    Inherits from `mptt.models.MPTTModel`.
    """

    released = models.BooleanField(default=False, verbose_name=_("released"))
    title = models.CharField(max_length=255, verbose_name=_("training set"))
    description = models.CharField(
        max_length=255, blank=True, verbose_name=_("description")
    )
    icon = models.ImageField(
        upload_to=convert_umlaute_images, blank=True, verbose_name=_("icon")
    )
    documents = models.ManyToManyField(
        Document, related_name="training_sets", verbose_name=_("document")
    )
    discipline = models.ManyToManyField(
        Discipline, related_name="training_sets", verbose_name=_("discipline")
    )
    created_by = models.ForeignKey(
        Group, on_delete=CASCADE, null=True, blank=True, verbose_name=_("created by")
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
    feedback = GenericRelation(Feedback)

    def image_tag(self):
        """
        Image thumbnail to display a preview of the icon

        :return: img HTML tag to display an image thumbnail
        :rtype: str
        """
        return get_image_tag(self.icon)

    image_tag.short_description = ""

    def __str__(self):
        """String representation of TrainingSet instance

        :return: title of training set instance
        :rtype: str
        """
        return self.title

    def save(self, *args, **kwargs):
        """Overwrite djangos save function to assure
        that no child elements are created.

        :raises ValidationError: Exception if child training set is created
        """
        if self.parent:
            msg = _(
                "It is not possible to create child elements for training sets (unlike disciplines)."
            )
            raise ValidationError(msg)
        super(TrainingSet, self).save(*args, **kwargs)

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of TrainingSet
        """

        verbose_name = _("training set")
        verbose_name_plural = _("training sets")

    def style_description_field(self):
        return format_html(
            '<div style="overflow-wrap: break-word; max-width: 150px;" >{}</div>',
            self.description,
        )

    style_description_field.short_description = "description"
