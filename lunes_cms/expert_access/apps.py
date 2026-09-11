from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExpertAccessConfig(AppConfig):
    """
    Application settings for the `expert_access` app.
    Inherits from `AppConfig`.
    """

    name = "lunes_cms.expert_access"
    verbose_name = _("expert access")

    def ready(self) -> None:
        """
        Let experts use the login screen of the admin, see
        :class:`~lunes_cms.expert_access.forms.ExpertAdminAuthenticationForm`.
        """
        # pylint: disable=import-outside-toplevel
        from django.contrib import admin

        from .forms import ExpertAdminAuthenticationForm

        admin.site.login_form = ExpertAdminAuthenticationForm
