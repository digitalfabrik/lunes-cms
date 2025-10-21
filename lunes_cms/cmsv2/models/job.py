from django.contrib.auth.models import Group
from django.db import models
from django.db.models.deletion import CASCADE
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _

from .static import convert_umlaute_images
from ..utils import get_child_count, get_image_tag


class Job(models.Model):
    """
    Model representing a job category.

    This model stores information about job categories, including their name, icon,
    and release status. Jobs can have multiple units associated with them.
    """

    released = models.BooleanField(default=False, verbose_name=_("released"))
    name = models.CharField(max_length=255, verbose_name=_("job"))
    icon = models.ImageField(
        upload_to=convert_umlaute_images, blank=True, verbose_name=_("icon")
    )
    v1_id = models.IntegerField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(
        Group,
        on_delete=CASCADE,
        null=True,
        blank=True,
        verbose_name=_("created by"),
        related_name="job",
    )
    creator_is_admin = models.BooleanField(default=True, verbose_name=_("admin"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_("modified at"))

    def is_valid(self):
        """
        Check if the job is valid for display.

        A job is considered valid if it has at least one child with training sets
        or at least one released unit.

        Returns:
            bool: True if the job is valid, False otherwise
        """
        return get_child_count(self) > 0 or self.units.filter(released=True).count() > 0

    def image_tag(self):
        """
        Generate an HTML image tag for the job's icon.

        Returns:
            str: HTML markup for displaying the job's icon
        """
        return get_image_tag(self.icon, width=120)

    image_tag.short_description = ""

    def list_icon(self):
        """
        Generate HTML for displaying the job's icon with controls in the admin list view.

        This method creates HTML that includes the icon image and buttons for adding,
        replacing, or deleting the icon.

        Returns:
            str: HTML markup for displaying the job's icon with controls
        """
        image_html = get_image_tag(self.icon, width=75)

        controls_html = f"""
        <div class="icon-controls" data-job-id="{self.id}">
            <button type="button" class="add-icon-btn" style="display: {'none' if self.icon else 'inline-flex'};">
                <span class="icon-add">+</span>
            </button>
            <button type="button" class="replace-icon-btn" style="display: {'inline-flex' if self.icon else 'none'};">
                <span class="icon-replace">↻</span>
            </button>
            <button type="button" class="delete-icon-btn" style="display: {'inline-flex' if self.icon else 'none'};">
                <span class="icon-delete">×</span>
            </button>
            <input type="file" class="icon-file-input" style="display: none;" accept="image/*">
        </div>
        """

        return mark_safe(
            f'<div class="job-icon-container">{image_html}{controls_html}</div>'
        )

    list_icon.short_description = _("Icon")

    def __str__(self):
        return str(self.name)

    class Meta:
        """
        Meta class for the Job model.

        This class defines metadata for the Job model, including verbose names
        for singular and plural forms.
        """

        verbose_name = _("Job")
        verbose_name_plural = _("Jobs")
