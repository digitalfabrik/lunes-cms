from django.contrib import admin
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _

from ..models import UnitWordRelation


class ReviewAdmin(admin.ModelAdmin):
    """
    Admin interface showing aggregated image review counts per unit-word relation.
    """

    list_display = ["word", "unit", "approval_count", "rejection_count"]
    list_display_links = None
    search_fields = ["word__word", "unit__title"]
    ordering = ["word__word"]

    def get_queryset(self, request):
        return (
            UnitWordRelation.objects.filter(image_reviews__isnull=False)
            .distinct()
            .annotate(
                approval_count=Count(
                    "image_reviews", filter=Q(image_reviews__status="APPROVED")
                ),
                rejection_count=Count(
                    "image_reviews", filter=Q(image_reviews__status="PENDING")
                ),
            )
            .select_related("word", "unit")
        )

    def has_add_permission(self, _request):
        return False

    def has_change_permission(self, _request, _obj=None):
        return False

    @admin.display(description=_("Approvals"), ordering="approval_count")
    def approval_count(self, obj):
        """Returns the number of approved reviews for this unit-word relation."""
        return obj.approval_count

    @admin.display(description=_("Rejections"), ordering="rejection_count")
    def rejection_count(self, obj):
        """Returns the number of rejected reviews for this unit-word relation."""
        return obj.rejection_count
