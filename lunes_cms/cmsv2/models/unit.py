from django.contrib.auth.models import Group
from django.db import models
from django.db.models.deletion import CASCADE
from django.urls import reverse
from django.utils.html import format_html, mark_safe, escape
from django.utils.translation import gettext_lazy as _

from .job import Job
from .static import convert_umlaute_images, Static
from .word import Word
from ..utils import get_image_tag
from ...core import settings


class UnitWordRelation(models.Model):
    """
    Model representing the relationship between Unit and Word models.

    This model serves as a through model for the many-to-many relationship between
    Unit and Word, allowing additional fields like image and image_check_status
    to be stored on the relationship.
    """

    unit = models.ForeignKey(
        "Unit", on_delete=models.CASCADE, related_name="unit_word_relations"
    )
    word = models.ForeignKey(
        Word, on_delete=models.CASCADE, related_name="unit_word_relations"
    )
    image = models.ImageField(
        upload_to=convert_umlaute_images, blank=True, verbose_name=_("image")
    )
    image_check_status = models.CharField(
        max_length=20,
        choices=Static.check_status_choices,
        null=True,
        verbose_name=_("image check status"),
        default="NOT_CHECKED",
    )

    def image_tag(self):
        """
        Generate an HTML image tag for the relation's image.

        Returns:
            str: HTML markup for displaying the image
        """
        return get_image_tag(self.image)

    image_tag.short_description = ""

    def save(self, *args, **kwargs):
        """
        Override the save method to handle image check status.

        This method ensures that when an image is updated, its check status is set to
        "NOT_CHECKED", and when an image is removed, its check status is set to None.
        """
        previous_relation = (
            UnitWordRelation.objects.get(pk=self.pk) if self.pk else None
        )
        image_updated = (not self.pk and self.image) or (
            self.pk and previous_relation and previous_relation.image != self.image
        )

        if image_updated:
            self.image_check_status = "NOT_CHECKED"

        if not self.image:
            self.image_check_status = None

        super().save(*args, **kwargs)

    def list_image(self):
        """
        Generate HTML for displaying the relation's image with controls in the admin list view.

        This method creates HTML that includes the image and buttons for adding,
        replacing, or deleting the image.

        Returns:
            str: HTML markup for displaying the image with controls
        """

        image_html = f'<a href="{escape(f"{settings.MEDIA_URL}{self.image}")}" target="_blank">{get_image_tag(self.image, width=75)}</a>'

        controls_html = f"""
        <div class="unitword-image-controls" data-unitword-id="{self.id}">
            <button type="button" class="add-unitword-image-btn" style="display: {'none' if self.image else 'inline-flex'};">
                <span class="unitword-image-add">+</span>
            </button>
            <button type="button" class="replace-unitword-image-btn" style="display: {'inline-flex' if self.image else 'none'};">
                <span class="unitword-image-replace">↻</span>
            </button>
            <button type="button" class="delete-unitword-image-btn" style="display: {'inline-flex' if self.image else 'none'};">
                <span class="unitword-image-delete">×</span>
            </button>
            <input type="file" class="unitword-image-file-input" style="display: none;" accept="image/*">
        </div>
        """

        return mark_safe(
            f'<div class="unitword-image-container">{image_html}{controls_html}</div>'
        )

    list_image.short_description = _("Image")

    def generate_image_link(self):
        """Generate link for image generation."""
        # return format_html("<div>{}</div>", self.pk)
        if self.pk:
            url = reverse("cmsv2:unitword_generate_image", args=[self.pk])
            return format_html('<a class="button" href="{}">Generate Image</a>', url)
        return "-"

    generate_image_link.short_description = _("Generate Image")

    class Meta:
        """
        Meta class for the UnitWordRelation model.

        This class defines metadata for the UnitWordRelation model, including verbose names
        for singular and plural forms, and a unique constraint on unit and word.
        """

        verbose_name = _("Unit-Word Relation")
        verbose_name_plural = _("Unit-Word Relations")
        unique_together = ("unit", "word")


class Unit(models.Model):
    """
    Represents a unit in the system, which can be linked to jobs and words.
    """

    released = models.BooleanField(default=False, verbose_name=_("released"))
    title = models.CharField(max_length=255, verbose_name=_("unit"))
    description = models.CharField(
        max_length=255, blank=True, verbose_name=_("description")
    )
    icon = models.ImageField(
        upload_to=convert_umlaute_images, blank=True, verbose_name=_("icon")
    )
    jobs = models.ManyToManyField(Job, related_name="units", verbose_name=_("job"))
    words = models.ManyToManyField(
        Word, through="UnitWordRelation", related_name="units", verbose_name=_("word")
    )
    created_by = models.ForeignKey(
        Group, on_delete=CASCADE, null=True, blank=True, verbose_name=_("created by")
    )
    creator_is_admin = models.BooleanField(default=True, verbose_name=_("admin"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_("modified at"))

    def image_tag(self):
        """
        Generates an HTML image tag for the unit's icon.

        Returns:
            str: An HTML <img> tag if an icon exists, otherwise an empty string.
        """
        return get_image_tag(self.icon)

    image_tag.short_description = ""

    def list_icon(self):
        """
        Generates an HTML representation of the unit's icon along with controls
        for adding, replacing, and deleting the icon. This is intended for display
        in list views, such as the Django admin.

        Returns:
            mark_safe: A `mark_safe` string containing the HTML for the icon and its controls.
        """
        image_html = get_image_tag(self.icon, width=75)

        # Add controls for adding, replacing, and deleting the icon
        controls_html = f"""
        <div class="icon-controls" data-unit-id="{self.id}">
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
            f'<div class="unit-icon-container">{image_html}{controls_html}</div>'
        )

    list_icon.short_description = _("Icon")

    def __str__(self):
        """
        Returns a string representation of the Unit, which is its title.

        Returns:
            str: The title of the unit.
        """
        return str(self.title)

    def style_description_field(self):
        """
        Formats the description field for display, ensuring text wraps and
        has a maximum width. This is useful for displaying descriptions in
        a more readable format in tables or list views.

        Returns:
            str: An HTML div containing the styled description.
        """
        return format_html(
            '<div style="overflow-wrap: break-word; max-width: 150px;" >{}</div>',
            self.description,
        )

    style_description_field.short_description = "description"

    class Meta:
        """
        Meta options for the Unit model.
        """

        verbose_name = _("Unit")
        verbose_name_plural = _("Units")
