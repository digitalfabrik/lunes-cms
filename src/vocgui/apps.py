from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class VocguiConfig(AppConfig):
    """
    Application settings for the `vocgui` app, which
    is our main cms app. Inherits from `AppConfig`.
    """

    name = "vocgui"
    verbose_name = _("vocabulary management")
