from django.contrib import admin


class BaseAdmin(admin.ModelAdmin):
    """
    Base admin class that automatically sets the created_by field based on the user's group.

    This class extends the ModelAdmin class and overrides the save_model method
    to automatically set the created_by field to the user's first group and
    set creator_is_admin based on whether the user is a superuser.
    """

    def save_model(self, request, obj, form, change):
        if not change:
            if len(request.user.groups.all()) >= 1:
                obj.created_by = request.user.groups.all()[0]
            elif not request.user.is_superuser:
                raise IndexError("No group assigned. Please add the user to a group")
            obj.creator_is_admin = request.user.is_superuser
        obj.save()
