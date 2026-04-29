"""
Custom admin views that render aggregated analytics as reports.

The views read from the daily aggregate tables (populated by the
``aggregate_analytics`` management command), so they never touch raw
``AnalyticsEvent`` rows and stay performant regardless of raw event volume.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import F, Sum
from django.db.models.expressions import Combinable
from django.db.models.functions import TruncMonth, TruncWeek
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from .models import SessionAggregate

#: Maps the ``granularity`` query parameter to the noun displayed for the column
#: header and the optional ``Trunc*`` function used to roll daily aggregate rows
#: up. ``None`` means "no truncation"; the ``date`` column is already daily so
#: ``TruncDate`` would only add a redundant cast that breaks on SQLite.
GRANULARITIES: dict[str, tuple[Any, Callable | None]] = {
    "daily": (_("Day"), None),
    "weekly": (_("Week"), TruncWeek),
    "monthly": (_("Month"), TruncMonth),
}


def _bucket_expression(granularity: str) -> Combinable:
    trunc = GRANULARITIES[granularity][1]
    return F("date") if trunc is None else trunc("date")


def _format_duration(total_seconds: int) -> str:
    """
    Render a duration in seconds as a compact string.

    Under a minute we show seconds, under an hour we show minutes and seconds,
    above we fall back to hours and minutes. Reports never need finer than
    second precision.
    """
    total_seconds = max(0, int(total_seconds))
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def _parse_range(request: HttpRequest) -> tuple[date, date, str]:
    granularity = request.GET.get("granularity", "daily")
    if granularity not in GRANULARITIES:
        granularity = "daily"

    today = date.today()
    try:
        end = (
            date.fromisoformat(request.GET["end"]) if request.GET.get("end") else today
        )
    except ValueError:
        end = today
    try:
        start = (
            date.fromisoformat(request.GET["start"])
            if request.GET.get("start")
            else end - timedelta(days=29)
        )
    except ValueError:
        start = end - timedelta(days=29)

    if start > end:
        start, end = end, start
    return start, end, granularity


def _session_rows(
    start: date, end: date, bucket_expr: Combinable
) -> list[dict[str, Any]]:
    rows_qs = (
        SessionAggregate.objects.filter(date__range=(start, end))
        .annotate(bucket=bucket_expr)
        .values("bucket")
        .annotate(
            total_sessions=Sum("total_sessions"),
            total_duration_seconds=Sum("total_duration_seconds"),
        )
        .order_by("bucket")
    )
    rows: list[dict[str, Any]] = []
    for row in rows_qs:
        sessions = row["total_sessions"] or 0
        duration_seconds = row["total_duration_seconds"] or 0
        avg_seconds = (duration_seconds / sessions) if sessions else 0
        rows.append(
            {
                "bucket": row["bucket"],
                "total_sessions": sessions,
                "total_duration_seconds": duration_seconds,
                "total_duration_display": _format_duration(duration_seconds),
                "avg_duration_seconds": round(avg_seconds, 1),
                "avg_duration_display": _format_duration(int(avg_seconds)),
            }
        )
    return rows


def _session_summary(start: date, end: date) -> dict[str, Any]:
    qs = SessionAggregate.objects.filter(date__range=(start, end)).aggregate(
        total_sessions=Sum("total_sessions"),
        total_duration_seconds=Sum("total_duration_seconds"),
    )
    sessions = qs["total_sessions"] or 0
    duration = qs["total_duration_seconds"] or 0
    avg = (duration / sessions) if sessions else 0
    return {
        "total_sessions": sessions,
        "total_duration_display": _format_duration(duration),
        "avg_duration_display": _format_duration(int(avg)),
    }


@staff_member_required
@user_passes_test(lambda u: u.is_superuser)
def sessions_report(request: HttpRequest) -> HttpResponse:
    """
    Total Session Duration report.

    Reads :class:`~lunes_cms.analytics.models.SessionAggregate` (one row per
    UTC day after aggregation) and rolls it up to the requested granularity.
    The aggregate table is keyed by an indexed unique ``date`` column, so a
    range query is cheap even over multi-year ranges.
    """
    start, end, granularity = _parse_range(request)
    granularity_label = GRANULARITIES[granularity][0]

    rows = _session_rows(start, end, _bucket_expression(granularity))
    chart_data = {
        "labels": [r["bucket"].isoformat() for r in rows],
        "bar": {
            "label": str(_("Sessions")),
            "values": [r["total_sessions"] for r in rows],
        },
        "line": {
            "label": str(_("Avg duration (s)")),
            "values": [r["avg_duration_seconds"] for r in rows],
        },
    }

    context = {
        **admin.site.each_context(request),
        "title": _("Total Session Duration"),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "granularity": granularity,
        "granularity_label": granularity_label,
        "rows": rows,
        "chart_data": chart_data,
        "summary": _session_summary(start, end),
    }
    return render(request, "admin/analytics/reports/sessions.html", context)
