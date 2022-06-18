from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HelpConfig(AppConfig):
    """
    Application settings for the `help` app,
    which is the app providing the public upload.
    Inherits from `AppConfig`.
    """

    name = "lunes_cms.help"
    verbose_name = _("help")
