from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CmsV2Config(AppConfig):
    """
    Application settings for the `cmsv2` app.
    Inherits from `AppConfig`.
    """

    name = "lunes_cms.cmsv2"
    verbose_name = _("Vocabulary Management v2")
