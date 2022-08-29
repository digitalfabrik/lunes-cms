from html import escape
from string import digits, ascii_uppercase

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils.html import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from qr_code.qrcode.maker import make_qr_code_url_with_args


def generate_default_token():
    """
    Generate a default random token of upper case letters and digits

    :return: A default token
    :rtype: str
    """
    return get_random_string(
        length=10, allowed_chars=digits + ascii_uppercase.replace("O", "")
    )


class GroupAPIKey(models.Model):
    """
    Model that handles api keys associated with a user group.
    """

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        verbose_name=_("group"),
        related_name="api_keys",
    )
    token = models.CharField(
        unique=True,
        max_length=50,
        verbose_name=_("token"),
        help_text=_("10-50 characters, only digits and upper case letters allowed."),
        validators=[
            MinLengthValidator(10),
            RegexValidator(
                r"^[0-9A-Z]*$", _("Only digits and upper case letters allowed")
            ),
        ],
        default=generate_default_token,
    )
    revoked = models.BooleanField(
        blank=True,
        default=False,
        verbose_name=_("revoked"),
        help_text=_("If the API key is revoked, clients cannot use it anymore."),
    )
    expiry_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("expiration date"),
        help_text=_("Once API key expires, clients cannot use it anymore."),
    )
    creation_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("creation date")
    )

    def is_valid(self):
        """
        An API key is valid if it is not revoked and the exiry date (if set) is not in the past.

        :return: Whether the API key is valid
        :rtype: bool
        """
        return not self.revoked and (not self.expiry_date or self.expiry_date > now())

    is_valid.boolean = True
    is_valid.short_description = _("valid")

    @property
    def qr_code_url(self):
        """
        :return: URL to the QR code for the token
        :rtype: str
        """
        return make_qr_code_url_with_args(
            data=self.token, qr_code_args={"image_format": "png"}
        )

    def qr_code_link(self, link, title=None):
        """
        :param link: The link text/image (needs to be properly escaped)
        :type link: str

        :param title: The link title (optional, needs to be properly escaped)
        :type title: str

        :return: HTML Link to the QR code for the token
        :rtype: str
        """
        return mark_safe(
            f'<a download="Lunes-QR-code-{escape(self.group.name)}.jpg" href="{escape(self.qr_code_url)}" title="{title or link}">{link}</a>'
        )

    def qr_code_download_link(self):
        """
        :return: Download link to the QR code for the token
        :rtype: str
        """
        return self.qr_code_link(escape(_("Download"))) if self.is_valid() else None

    qr_code_download_link.short_description = _("QR code")

    def qr_code(self):
        """
        :return: QR code image for the token with download link
        :rtype: str
        """
        return (
            self.qr_code_link(
                mark_safe(
                    f'<img src="{escape(self.qr_code_url)}" width="330" height="auto" /></a>'
                ),
                escape(_("Download QR code")),
            )
            if self.is_valid()
            else "-"
        )

    qr_code.short_description = _("QR code")

    @classmethod
    def get_from_token(cls, token):
        try:
            return cls.objects.get(
                Q(token=token, revoked=False)
                & (Q(expiry_date__isnull=True) | Q(expiry_date__gt=now()))
            )
        except cls.DoesNotExist:
            raise PermissionDenied()

    def __str__(self):
        """
        :return: The canonical string representation of an API key
        :rtype: str
        """
        return _('{}: Token for the group "{}"').format(self.token, self.group)

    class Meta:
        verbose_name = _("API Key")
        verbose_name_plural = _("API Keys")
