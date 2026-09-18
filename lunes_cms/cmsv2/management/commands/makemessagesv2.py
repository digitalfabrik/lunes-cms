from typing import Any

from django.core.management.commands import makemessages


class Command(makemessages.Command):
    """
    Custom makemessages command to reduce some of our annoyances with po files.
    """

    def handle(self, *args: Any, **options: Any) -> str | None:
        self.msgmerge_options += ["--no-fuzzy-matching"]
        return super().handle(*args, **options)
