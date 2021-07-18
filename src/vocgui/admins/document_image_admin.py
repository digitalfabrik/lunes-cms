from django.contrib import admin

from vocgui.models import DocumentImage

class DocumentImageAdmin(admin.StackedInline):
    """
    Admin Interface to for the DocumentImage module.
    Inheriting from `admin.StackedInline`.
    """

    model = DocumentImage
    search_fields = ["name"]
    fields = ["name", "image", "image_tag", "confirmed"]
    readonly_fields = ["image_tag"]
    autocomplete_fields = ["document"]
    insert_after = "autocomplete_fields"
    extra = 0

    def get_form(self, request, obj=None, **kwargs):
        """
        Modify user form since normal users shouldn't
        see a confirmed button. This is only neccessary
        for superusers.

        :param request: current user request
        :type request: django.http.request
        :param obj: django model object, defaults to None
        :type obj: django.db.models, optional
        :return: model form with adjustet fields
        :rtype: ModelForm
        """
        self.exclude = []
        if not request.user.is_superuser:
            self.exclude.append("confirmed")
        return super(DocumentImageAdmin, self.get_form(request, obj, **kwargs))

