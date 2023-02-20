from django.contrib import admin

from django.utils.translation import ugettext_lazy as _


class SponsorAdmin(admin.ModelAdmin):
    """
    Admin interface that is used to edit sponsor objects in the CMS.
    """

    fields = [
        "name",
        "icon",
    ]
    list_display = [
        "name",
        "icon_is_set",
    ]
    list_per_page = 25
