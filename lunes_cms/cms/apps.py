from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CmsConfig(AppConfig):
    """
    Application settings for the `cms` app, which
    is our main cms app. Inherits from `AppConfig`.
    """

    name = "lunes_cms.cms"
    verbose_name = _("vocabulary management")
