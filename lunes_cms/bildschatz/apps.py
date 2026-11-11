from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BildschatzConfig(AppConfig):
    """
    Application settings for the `bildschatz` app,
    which serves the public Bildschatz image database website.
    Inherits from `AppConfig`.
    """

    name = "lunes_cms.bildschatz"
    verbose_name = _("Bildschatz")
