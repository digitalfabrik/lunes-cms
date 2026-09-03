from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExpertAccessConfig(AppConfig):
    """
    Application settings for the `expert_access` app.
    Inherits from `AppConfig`.
    """

    name = "lunes_cms.expert_access"
    verbose_name = _("expert access")
