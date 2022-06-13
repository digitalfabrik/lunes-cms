from html import escape

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.text import Truncator


class Feedback(models.Model):
    """
    Model to store feedback about disciplines, training sets and vocabulary words
    """

    content_type = models.ForeignKey(
        ContentType,
        limit_choices_to=models.Q(
            app_label="cms", model__in=["discipline", "trainingset", "document"]
        ),
        on_delete=models.CASCADE,
        verbose_name=_("content type"),
        help_text=_("The content type this feedback entry refers to."),
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_("object id"),
        help_text=_("The id of the object this feedback entry refers to."),
    )
    content_object = GenericForeignKey("content_type", "object_id")
    content_object.short_description = _("refers to")

    comment = models.TextField(
        verbose_name=_("comment"),
    )

    read_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedback",
        verbose_name=_("marked as read by"),
        help_text=_(
            "The user who marked this feedback as read. If the feedback is unread, this field is empty."
        ),
    )

    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("submitted on"),
        help_text=_("The time and date when the feedback was submitted."),
    )

    def content_object_link(self):
        """
        Include a link to the edit form of the content object in list display

        :return: Link to the edit form of the content object
        :rtype: str
        """
        # Get link to the admin form if the content object
        admin_edit_link = reverse(
            f"admin:cms_{self.content_type.model}_change", args=[self.object_id]
        )
        # Escape label because string is marked as safe afterwards
        escaped_label = escape(str(self.content_object))
        # Mark string as safe to allow html link tag
        return mark_safe(f"<a href={admin_edit_link}>{escaped_label}</a>")

    content_object_link.short_description = _("refers to")

    def __str__(self):
        """
        String representation of feedback instance

        :return: Truncated feedback comment
        :rtype: str
        """
        return Truncator(self.comment).chars(80)

    class Meta:
        #: The verbose name of the model
        verbose_name = _("feedback")
        #: The plural verbose name of the model
        verbose_name_plural = _("feedback entries")
