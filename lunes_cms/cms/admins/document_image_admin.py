from django.contrib import admin

from ..models import DocumentImage


class DocumentImageAdmin(admin.StackedInline):
    """
    Admin Interface to for the DocumentImage module.
    Inheriting from `admin.StackedInline`.
    """

    model = DocumentImage
    fields = ["image", "image_tag"]
    superuser_fields = ["confirmed"]
    readonly_fields = ["image_tag"]
    autocomplete_fields = ["document"]
    insert_after = "autocomplete_fields"
    extra = 0

    def get_fields(self, request, obj=None):
        """
        Override djangos get_fields function
        to add custom superuser fields to the
        admin interface if the user has the corresponding
        access rights.

        :param request: current request
        :type request: django.http.request
        :param obj: [description], defaults to None
        :type obj: django.db.models, optional

        :return: custom fields list
        :rtype: list[str]
        """
        if request.user.is_superuser and self.superuser_fields:
            return (self.fields or tuple()) + self.superuser_fields
        return super(DocumentImageAdmin, self).get_fields(request, obj)
