from rest_framework_api_key.admin import APIKeyModelAdmin


class GroupAPIKeyAdmin(APIKeyModelAdmin):
    exclude = ("objects",)
    list_display = [*APIKeyModelAdmin.list_display, "organization"]
    search_fields = [*APIKeyModelAdmin.search_fields, "organization"]
    list_per_page = 25
