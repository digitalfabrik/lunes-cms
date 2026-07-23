from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AnalysisConfig(AppConfig):
    """
    Application settings for the `analysis` app, which groups analysis/report
    pages (currently just "Duplicated vocabulary", issue #531) under their
    own "Analyse" section in the admin sidebar, separate from the actual
    vocabulary CRUD apps.
    """

    name = "lunes_cms.analysis"
    verbose_name = _("Analysis")
