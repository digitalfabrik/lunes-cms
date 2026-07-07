from __future__ import annotations

from typing import Any

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.core.files.base import File


class LaxManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """ManifestStaticFilesStorage that silently skips unresolvable references.

    Third-party minified files (e.g. Bootstrap bundles) may contain
    sourceMappingURL comments pointing to .map files that are not part of our
    static files collection.  Django's ``manifest_strict = False`` does not
    cover all code paths in newer versions, so we also override ``hashed_name``
    to return the original name when a referenced file cannot be found.
    """

    manifest_strict = False

    def hashed_name(
        self, name: str, content: File[Any] | None = None, filename: str | None = None
    ) -> str:
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            return name


def strtobool(string: str) -> int:
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'string' is anything else.
    """
    string = string.lower()
    if string in ("y", "yes", "t", "true", "on", "1"):
        return 1
    if string in ("n", "no", "f", "false", "off", "0"):
        return 0
    raise ValueError(f"invalid truth value {string}")
