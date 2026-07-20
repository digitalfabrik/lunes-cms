from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _escape_field_string(value: str) -> str:
    """Escape special characters in InfluxDB line protocol string field values."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def date_to_ns(d: date) -> int:
    """Convert a date to a nanosecond Unix timestamp at midnight UTC."""
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000_000)


def resolve_job(job_id: int | str | None, job_names: dict[int, str]) -> str | None:
    """Return an escaped job name for use as an InfluxDB string field value.

    Returns None if job_id is None, or a fallback string if the id is not found.
    """
    if job_id is None:
        return None
    name = job_names.get(int(job_id), f"unknown_{job_id}")
    return _escape_field_string(name)


def resolve_unit(unit_id: int | str | None, unit_names: dict[int, str]) -> str | None:
    """Return an escaped unit title for use as an InfluxDB string field value.

    Returns None if unit_id is None, or a fallback string if the id is not found.
    """
    if unit_id is None:
        return None
    name = unit_names.get(int(unit_id), f"unknown_{unit_id}")
    return _escape_field_string(name)


def push_lines(lines: list[str]) -> None:
    """Push InfluxDB line protocol lines to the configured write endpoint.

    Raises on failure so callers that push before committing their DB
    transaction (see aggregate_analytics) can roll back the corresponding
    ``aggregated_at`` markers instead of losing data silently.
    """
    if not lines:
        return
    try:
        response = requests.post(
            settings.INFLUX_URL,
            params={"db": settings.INFLUX_DB},
            data="\n".join(lines).encode(),
            cert=(settings.INFLUX_CERT, settings.INFLUX_KEY),
            verify=settings.INFLUX_CA,
            timeout=10,
        )
        response.raise_for_status()
        logger.debug(
            "Pushed %d lines to InfluxDB (db=%s)", len(lines), settings.INFLUX_DB
        )
    except Exception as exc:
        logger.error("InfluxDB push failed (%d lines): %s", len(lines), exc)
        raise
