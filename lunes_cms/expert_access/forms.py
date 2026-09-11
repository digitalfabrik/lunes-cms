from __future__ import annotations

from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from ..cmsv2.models.static import is_expert


class ExpertAdminAuthenticationForm(AdminAuthenticationForm):
    """
    The login form of the admin, changed so that experts can also log in.
    """

    def confirm_login_allowed(self, user: User) -> None:
        """
        Reject everyone who may not use this login screen.

        :param user: the user who just authenticated

        :raises django.core.exceptions.ValidationError: if the user does not have permission to log in
        """
        if is_expert(user):
            AuthenticationForm.confirm_login_allowed(self, user)
        else:
            super().confirm_login_allowed(user)
