from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.utils import check_openai_availability


class CmsV2Config(AppConfig):
    """
    Application settings for the `cmsv2` app.
    Inherits from `AppConfig`.
    """

    name = "lunes_cms.cmsv2"
    verbose_name = _("Vocabulary Management v2")

    def ready(self):
        """
        Called when the app is ready.
        Performs startup checks including OpenAI availability.
        """
        check_openai_availability()
