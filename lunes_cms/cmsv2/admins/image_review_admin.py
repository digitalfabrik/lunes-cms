from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models.static import PENDING_REVIEW_STATUSES
from lunes_cms.cmsv2.utils import get_image_tag
from lunes_cms.core import settings


class ImageReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for the ImageReview model.

    Allows reviewers to inspect and update the review status of word images.
    Non-superusers only see reviews assigned to themselves. Superusers see all.
    """

    list_display = [
        "image_preview",
        "word_display",
        "job_display",
        "unit_display",
        "is_unit_specific_image",
        "status",
    ]
    list_display_links = ["word_display"]
    search_fields = [
        "unit_word_relation__word__word",
        "unit_word_relation__unit__title",
    ]
    readonly_fields = [
        "reviewer",
        "unit_word_relation",
        "is_unit_specific_image",
        "image_preview",
        "created_at",
        "updated_at",
    ]
    fields = [
        "image_preview",
        "unit_word_relation",
        "status",
        "comment",
        "suggested_image",
        "reviewer",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    list_per_page = 25

    def _base_queryset(self, request):
        """
        Base queryset filtered by reviewer — without any status filter.
        Used to compute tab counts across all statuses.
        """
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(reviewer=request.user)
        return qs

    def get_queryset(self, request):
        """
        Restrict the queryset to the current user's reviews unless they are a superuser,
        and apply the active status tab filter from the URL parameter.
        Default (no parameter or ?status=PENDING) shows all pending items.
        """
        qs = self._base_queryset(request)
        status_param = request.GET.get("status")
        if status_param == "APPROVED":
            return qs.filter(status="APPROVED")
        if status_param == "REJECTED":
            return qs.filter(status="REJECTED")
        # Default: show all pending statuses
        return qs.filter(status__in=PENDING_REVIEW_STATUSES)

    def changelist_view(self, request, extra_context=None):
        """
        Inject per-status counts into the template context for the tab badges.
        Uses the base queryset (without status filter) so all tabs always show
        correct totals regardless of the active tab.
        """
        qs = self._base_queryset(request)
        extra_context = extra_context or {}
        extra_context["status_counts"] = {
            "PENDING": qs.filter(status__in=PENDING_REVIEW_STATUSES).count(),
            "APPROVED": qs.filter(status="APPROVED").count(),
            "REJECTED": qs.filter(status="REJECTED").count(),
        }
        return super().changelist_view(request, extra_context=extra_context)

    def _is_expert(self, request):
        return request.user.groups.filter(name="Expert:innen").exists()

    def has_view_permission(self, request, obj=None):
        return self._is_expert(request)

    def has_change_permission(self, request, obj=None):
        return self._is_expert(request)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def word_display(self, obj):
        """Display the word being reviewed."""
        return obj.word

    def job_display(self, obj):
        """Display the job(s) that the vocabulary belongs to."""
        jobs = obj.unit_word_relation.unit.jobs.all()
        if not jobs.exists():
            return "-"
        return ", ".join(str(j) for j in jobs)

    word_display.short_description = _("word")  # type: ignore[attr-defined]
    job_display.short_description = _("job")  # type: ignore[attr-defined]
    word_display.admin_order_field = "unit_word_relation__word__word"  # type: ignore[attr-defined]

    def unit_display(self, obj):
        """Display the unit context of the review."""
        return obj.unit

    unit_display.short_description = _("unit")  # type: ignore[attr-defined]
    unit_display.admin_order_field = "unit_word_relation__unit__title"  # type: ignore[attr-defined]

    def image_preview(self, obj):
        """
        Display a thumbnail of the image being reviewed with a link to the full version.
        """
        image = obj.reviewed_image
        if image:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                f"{settings.MEDIA_URL}{image}",
                mark_safe(get_image_tag(image, width=80)),
            )
        return _("No image available.")

    image_preview.short_description = _("image preview")  # type: ignore[attr-defined]
