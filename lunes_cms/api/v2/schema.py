"""
Postprocessing hooks for the v2 API schema
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.generators import SchemaGenerator

TRACKING_HEADERS = [
    {
        "in": "header",
        "name": "X-os",
        "schema": {"type": "string", "enum": ["android", "ios"]},
        "description": "Operating system of the client",
        "required": False,
    },
    {
        "in": "header",
        "name": "X-os-version",
        "schema": {"oneOf": [{"type": "string"}, {"type": "number"}]},
        "description": "Version of the client operating system",
        "required": False,
    },
    {
        "in": "header",
        "name": "X-app-version",
        "schema": {"type": "string"},
        "description": "Version of lunes app",
        "required": False,
    },
]

TRACKING_HEADER_METHODS = {"get", "post"}


def add_tracking_headers(
    result: dict[str, Any],
    _generator: SchemaGenerator,
    _request: Any,
    _public: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """
    Hook into schema generation to add the tracking headers to all endpoints in `/api/v2`
    """
    for path, path_item in result.get("paths", {}).items():
        if not path.startswith("/api/v2/"):
            continue
        for key, operation in path_item.items():
            if key not in TRACKING_HEADER_METHODS:
                continue
            operation.setdefault("parameters", [])
            operation["parameters"].extend(TRACKING_HEADERS)
    return result
