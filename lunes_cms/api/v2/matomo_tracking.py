"""
Matomo tracking decorator for API v2 endpoints.

This module provides a decorator to track API requests to Matomo asynchronously,
without blocking the main request/response cycle.
"""

import atexit
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional
from urllib import error, parse
from urllib import request as urllib_request

from django.conf import settings

logger = logging.getLogger(__name__)

# Module-level thread pool executor for Matomo tracking requests.
# Reuses threads instead of creating new ones for each request.
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="matomo_tracking")

# Ensure clean shutdown of the thread pool when the application exits
atexit.register(_executor.shutdown, wait=False)


@dataclass
class MatomoTrackingData:  # pylint: disable=too-many-instance-attributes
    """Data class to hold Matomo tracking information."""

    matomo_url: str
    site_id: str
    token: str
    action_name: str
    category: str
    request_url: str
    user_agent: str
    os: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    resource_id: Optional[str] = None


def send_matomo_tracking(tracking_data: MatomoTrackingData) -> None:
    """
    Send tracking data to Matomo API.

    This function is designed to be called in a separate thread
    to avoid blocking the main request.

    :param tracking_data: MatomoTrackingData instance containing all tracking info
    """
    data = {
        "idsite": tracking_data.site_id,
        "rec": 1,
        "apiv": 1,
        "url": tracking_data.request_url,
        "ua": tracking_data.user_agent,
        "action_name": tracking_data.category + "/" + tracking_data.action_name,
    }

    # Add authentication token if provided
    if tracking_data.token:
        data["token_auth"] = tracking_data.token

    # Add custom dimensions
    if tracking_data.os:
        data["dimension1"] = tracking_data.os
    if tracking_data.os_version:
        data["dimension2"] = tracking_data.os_version
    if tracking_data.app_version:
        data["dimension3"] = tracking_data.app_version
    if tracking_data.resource_id:
        data["dimension4"] = tracking_data.resource_id

    data_str = parse.urlencode(data)
    url = f"{tracking_data.matomo_url}/matomo.php?{data_str}"

    try:
        req = urllib_request.Request(url)
        with urllib_request.urlopen(req, timeout=10):
            pass
        logger.debug(
            "Matomo tracking sent successfully for action: %s",
            tracking_data.action_name,
        )
    except error.HTTPError as e:
        # Mask the token in logs for security
        safe_url = url
        if tracking_data.token:
            safe_url = url.replace(
                f"token_auth={tracking_data.token}", "token_auth=********"
            )
        logger.error(
            "Matomo tracking API request failed with HTTP error %s: %s - URL: %s",
            e.code,
            e.reason,
            safe_url,
        )
    except error.URLError as e:
        logger.error("Matomo tracking API request failed: %s", e.reason)
    except (OSError, TimeoutError) as e:
        logger.error("Unexpected error during Matomo tracking: %s", str(e))


def matomo_tracking(
    action_name: str,
    category: str = "API",
    resource_id: Optional[str] = None,
) -> Callable:
    """
    Decorator for tracking API endpoint access in Matomo.

    This decorator wraps DRF ViewSet action methods to send tracking data
    asynchronously to Matomo without blocking the original request.

    :param action_name: Name of the action to track (sent as action_name to Matomo)
    :param category: Category of the event (default: "API")
    :param resource_id: Optional URL kwarg key to extract as "id" dimension
                        (e.g., "pk", "job_id", "unit_id")
    :return: Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, http_request, *args: Any, **kwargs: Any):
            # Execute the original function first
            response = func(self, http_request, *args, **kwargs)

            # Skip tracking if Matomo is not configured or not enabled
            if (
                not settings.MATOMO_TRACKING
                or not settings.MATOMO_URL
                or not settings.MATOMO_SITE_ID
            ):
                return response

            # Extract id from URL kwargs if specified
            tracking_id = None
            if resource_id and resource_id in kwargs:
                tracking_id = str(kwargs[resource_id])

            # Create tracking data object
            tracking_data = MatomoTrackingData(
                matomo_url=settings.MATOMO_URL,
                site_id=settings.MATOMO_SITE_ID,
                token=settings.MATOMO_TOKEN,
                action_name=action_name,
                category=category,
                request_url=http_request.build_absolute_uri(),
                user_agent=http_request.META.get("HTTP_USER_AGENT", "unknown"),
                os=http_request.META.get("HTTP_X_OS"),
                os_version=http_request.META.get("HTTP_X_OS_VERSION"),
                app_version=http_request.META.get("HTTP_X_APP_VERSION"),
                resource_id=tracking_id,
            )

            # Send tracking request asynchronously using the thread pool
            _executor.submit(send_matomo_tracking, tracking_data)

            return response

        return wrapper

    return decorator
