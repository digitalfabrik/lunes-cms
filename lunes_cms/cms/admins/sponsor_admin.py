from django.contrib import admin


class SponsorAdmin(admin.ModelAdmin):
    """
    Admin interface that is used to edit sponsor objects in the CMS.
    """
    list_display = [
        "name",
        "icon",
    ]
    list_per_page = 25