from django.contrib import admin

from ..models import RegisterUserForm


class UserAdmin(admin.ModelAdmin):
    fields = ("password", "email", "username")
