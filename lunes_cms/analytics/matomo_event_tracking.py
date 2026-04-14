"""
Matomo event tracking for analytics events.

Forwards analytics events to Matomo using its Event Tracking API,
reusing the existing Matomo configuration and async execution pattern.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib import error, parse
from urllib import request as urllib_request

from django.conf import settings
from rest_framework.request import Request

from lunes_cms.api.v2.matomo_tracking import executor

logger = logging.getLogger(__name__)


@dataclass
class MatomoEventData:  # pylint: disable=too-many-instance-attributes
    """Data class to hold Matomo event tracking parameters."""

    matomo_url: str
    site_id: str
    token: str
    url: str
    user_agent: str
    event_category: str
    event_action: str
    event_name: str
    event_value: Optional[float] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None


def send_matomo_event(data: MatomoEventData) -> None:
    """
    Send event tracking data to Matomo API.

    This function is designed to be called in a separate thread
    to avoid blocking the main request.

    :param data: MatomoEventData instance containing all event tracking info
    """
    params: dict[str, Any] = {
        "idsite": data.site_id,
        "rec": 1,
        "apiv": 1,
        "url": data.url,
        "ua": data.user_agent,
        "e_c": data.event_category,
        "e_a": data.event_action,
        "e_n": data.event_name,
    }

    if data.event_value is not None:
        params["e_v"] = data.event_value

    if data.token:
        params["token_auth"] = data.token

    if data.os:
        params["dimension1"] = data.os
    if data.os_version:
        params["dimension2"] = data.os_version
    if data.app_version:
        params["dimension3"] = data.app_version

    url = f"{data.matomo_url}/matomo.php?{parse.urlencode(params)}"

    try:
        req = urllib_request.Request(url)
        with urllib_request.urlopen(req, timeout=10):
            pass
        logger.debug(
            "Matomo event sent successfully: %s/%s",
            data.event_action,
            data.event_name,
        )
    except error.HTTPError as e:
        safe_url = url
        if data.token:
            safe_url = url.replace(f"token_auth={data.token}", "token_auth=********")
        logger.error(
            "Matomo event API request failed with HTTP error %s: %s - URL: %s",
            e.code,
            e.reason,
            safe_url,
        )
    except error.URLError as e:
        logger.error("Matomo event API request failed: %s", e.reason)
    except (OSError, TimeoutError) as e:
        logger.error("Unexpected error during Matomo event tracking: %s", str(e))


def _build_job_selected(
    payload: dict[str, Any],
) -> tuple[str, Optional[float]]:
    return (f"job:{payload['job_id']}:{payload['action']}", None)


def _build_session_start(
    payload: dict[str, Any],
) -> tuple[str, Optional[float]]:
    return (f"session:{payload['session_id']}", None)


def _build_session_end(
    payload: dict[str, Any],
) -> tuple[str, Optional[float]]:
    return (f"session:{payload['session_id']}", None)


def _build_module_duration(
    payload: dict[str, Any],
) -> tuple[str, Optional[float]]:
    return (
        f"unit:{payload['unit_id']}:exercise:{payload['exercise_type']}",
        float(payload["duration_seconds"]),
    )


def _build_exercise_dropout(
    payload: dict[str, Any],
) -> tuple[str, Optional[float]]:
    unit_id = payload["unit_id"] if payload["unit_id"] is not None else "unknown"
    return (
        f"unit:{unit_id}:exercise:{payload['exercise_type']}:pos:{payload['position']}/{payload['total']}",
        float(payload["position"]),
    )


EVENT_NAME_BUILDERS: dict[
    str, Callable[[dict[str, Any]], tuple[str, Optional[float]]]
] = {
    "job_selected": _build_job_selected,
    "session_start": _build_session_start,
    "session_end": _build_session_end,
    "module_duration": _build_module_duration,
    "exercise_dropout": _build_exercise_dropout,
}


def forward_analytics_event_to_matomo(
    event_type: str, payload: dict[str, Any], request: Request
) -> None:
    """
    Forward an analytics event to Matomo asynchronously.

    :param event_type: The type of analytics event
    :param payload: The event payload dict
    :param request: The originating HTTP request
    """
    if (
        not settings.MATOMO_TRACKING
        or not settings.MATOMO_URL
        or not settings.MATOMO_SITE_ID
    ):
        return

    builder = EVENT_NAME_BUILDERS.get(event_type)
    if builder is None:
        logger.warning("No Matomo event builder for event type: %s", event_type)
        return

    event_name, event_value = builder(payload)

    data = MatomoEventData(
        matomo_url=settings.MATOMO_URL,
        site_id=settings.MATOMO_SITE_ID,
        token=settings.MATOMO_TOKEN,
        url=request.build_absolute_uri(),
        user_agent=request.META.get("HTTP_USER_AGENT", "unknown"),
        event_category="analytics",
        event_action=event_type,
        event_name=event_name,
        event_value=event_value,
        os=request.META.get("HTTP_X_OS"),
        os_version=request.META.get("HTTP_X_OS_VERSION"),
        app_version=request.META.get("HTTP_X_APP_VERSION"),
    )

    executor.submit(send_matomo_event, data)
