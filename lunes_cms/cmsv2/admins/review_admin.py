from django.contrib import admin
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ..models import UnitWordRelation


class ReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for managing reviews of unit-word relations
    """

    list_display = ["word", "unit", "approval_count", "rejection_count", "more_options"]
    search_fields = ["word__word", "unit__title"]

    def has_add_permission(self, request):
        """
        Disables `add` button in the admin interface
        """
        return False

    def get_queryset(self, request):
        """
        Queryset with annotated counts of approved and pending image reviews for each unit-word relation.
        """
        queryset = super().get_queryset(request)
        return queryset.annotate(
            approval_count=Count(
                "image_reviews", filter=Q(image_reviews__status="APPROVED")
            ),
            rejection_count=Count(
                "image_reviews", filter=Q(image_reviews__status="PENDING")
            ),
        )

    def get_urls(self):
        """
        Get Url for button to confirm image in the admin interface
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/confirm-image/",
                self.admin_site.admin_view(self.confirm_image_view),
                name="cmsv2_unitwordrelation_confirm_image",
            ),
        ]
        return custom_urls + urls

    def confirm_image_view(self, request, pk):
        """
        Method to confirm image
        """
        UnitWordRelation.objects.filter(pk=pk).update(image_check_status="CONFIRMED")
        unitword = UnitWordRelation.objects.get(pk=pk)
        self.message_user(
            request, _(f"Image '{unitword.word}' was marked as confirmed.")
        )
        return HttpResponseRedirect(reverse("admin:cmsv2_unitwordrelation_changelist"))

    @admin.display(description=_("Approvals"), ordering="approval_count")
    def approval_count(self, obj):
        """Returns the number of approvals for the unit-word relation."""
        return obj.approval_count

    @admin.display(description=_("Rejections"), ordering="rejection_count")
    def rejection_count(self, obj):
        """Returns the number of rejections for the unit-word relation."""
        return obj.rejection_count

    @admin.display(description=_("actions"))
    def more_options(self, obj):
        """Returns a button to confirm the image if there are approvals and no rejections, and possible more options in the future."""
        if obj.approval_count > 1 and obj.rejection_count == 0:
            url = reverse("admin:cmsv2_unitwordrelation_confirm_image", args=[obj.pk])
            return format_html('<a class="button" href="{}">Image bestätigen</a>', url)
        return ""
