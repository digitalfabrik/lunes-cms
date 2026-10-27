"""
Management command to send every expert one email with all new content to
review since the last run, see :func:`~lunes_cms.cmsv2.notifications.send_digests`.

Meant to run weekly via cron, see ``example-configs/lunes-cms.cron.example``.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.utils import translation

from lunes_cms.cmsv2.notifications import send_digests


class Command(BaseCommand):
    """Management command to send the pending notifications to the experts."""

    help = "Send every expert one email with all pending notifications."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--language",
            choices=[code for code, _name in settings.LANGUAGES],
            default=settings.LANGUAGE_CODE,
            help=f"Language of the emails (default: {settings.LANGUAGE_CODE})",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        with translation.override(options["language"]):
            sent = send_digests()
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} digest(s)"))
