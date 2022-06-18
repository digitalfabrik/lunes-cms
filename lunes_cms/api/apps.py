from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ApiConfig(AppConfig):
    """
    Application settings for the `api` app,
    which is the app providing the REST API.
    Inherits from `AppConfig`.
    """

    name = "lunes_cms.api"
    verbose_name = _("API")
