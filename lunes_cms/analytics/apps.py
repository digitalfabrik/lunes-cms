from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AnalyticsConfig(AppConfig):
    """
    Application settings for the ``analytics`` app, which stores raw events
    plus their daily aggregate tables and exposes admin report views.
    """

    name = "lunes_cms.analytics"
    verbose_name = _("Analytics")
