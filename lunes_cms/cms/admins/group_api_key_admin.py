from django.contrib import admin


class GroupAPIKeyAdmin(admin.ModelAdmin):
    list_display = [
        "token",
        "group",
        "is_valid",
        "expiry_date",
        "qr_code_download_link",
    ]
    search_fields = ["group"]
    readonly_fields = ["is_valid", "qr_code"]
    list_per_page = 25
