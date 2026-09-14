from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ActivationConfig(AppConfig):
    """
    Application settings for the `activation` app,
    which is the app providing the public activation landing page.
    Inherits from `AppConfig`.
    """

    name = "lunes_cms.activation"
    verbose_name = _("activation")
