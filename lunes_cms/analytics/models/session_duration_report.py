from django.utils.translation import gettext_lazy as _

from .session_aggregate import SessionAggregate


class SessionDurationReport(SessionAggregate):
    """
    Virtual proxy model used solely to surface the Total Session Duration
    report in the Django admin sidebar. It shares the ``SessionAggregate``
    table but its ``ModelAdmin`` redirects every list view straight to the
    sessions report, so the model is never actually browsed as rows.
    """

    class Meta:
        """Meta class"""

        proxy = True
        verbose_name = _("Total Session Duration")
        verbose_name_plural = _("Total Session Duration")
        permissions = [
            ("can_view_analytics", _("Can view analytics")),
        ]
