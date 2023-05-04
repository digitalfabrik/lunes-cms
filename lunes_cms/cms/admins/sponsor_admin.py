from django.contrib import admin

from django.utils.translation import ugettext_lazy as _

from ..utils import get_image_tag


class SponsorAdmin(admin.ModelAdmin):
    """
    Admin interface that is used to edit sponsor objects in the CMS.
    """

    fields = [
        "name",
        "url",
        "logo",
        "image_tag",
    ]
    readonly_fields = ["image_tag"]
    list_display = [
        "name",
        "has_logo",
    ]
    list_per_page = 25

    def has_logo(self, obj):
        """
        Additional field to display whether a logo is set for the sponsor in the list view.

        :return: Whether the sponsor has a logo
        :rtype: bool
        """

        return bool(obj.logo)

    has_logo.boolean = True
    has_logo.short_description = _("logo")

    def image_tag(self, obj):
        """
        Image thumbnail to display a preview of a image in the form view.

        :return: img HTML tag to display an image thumbnail
        :rtype: str
        """
        return get_image_tag(obj.logo)

    image_tag.short_description = ""

    class Media:
        js = ("js/image_preview.js",)
