from django.contrib import admin


class GroupAPIKeyAdmin(admin.ModelAdmin):
    list_display = ["token", "group", "is_valid", "expiry_date"]
    search_fields = ["group"]
    readonly_fields = ["is_valid"]
    list_per_page = 25
