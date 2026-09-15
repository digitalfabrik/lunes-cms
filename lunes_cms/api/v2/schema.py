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

#: The answer of the content endpoints to an access token that cannot be
#: resolved. The REST framework raises this from the authentication class, so
#: it is not derived from any view and has to be documented here.
INVALID_TOKEN_RESPONSE = {
    "description": "The area access token could not be resolved.",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "error": {"type": "string", "enum": ["invalid_area_token"]},
                },
            }
        }
    },
}


def add_tracking_headers(
    result: dict[str, Any],
    generator: SchemaGenerator,  # pylint: disable=unused-argument
    request: Any,  # pylint: disable=unused-argument
    public: bool,  # pylint: disable=unused-argument
    **_kwargs: Any,
) -> dict[str, Any]:
    """
    Hook into schema generation to add the tracking headers to all endpoints in `/api/v2`

    drf-spectacular calls the postprocessing hooks with keyword arguments, so
    the names of the parameters are part of the interface and must not be
    prefixed with an underscore, however unused they are.
    """
    for path, path_item in result.get("paths", {}).items():
        if not path.startswith("/api/v2/"):
            continue
        for key, operation in path_item.items():
            if key not in TRACKING_HEADER_METHODS:
                continue
            operation.setdefault("parameters", [])
            operation["parameters"].extend(TRACKING_HEADERS)
            if any("areaToken" in scheme for scheme in operation.get("security", [])):
                operation.setdefault("responses", {}).setdefault(
                    "401", INVALID_TOKEN_RESPONSE
                )
    return result
