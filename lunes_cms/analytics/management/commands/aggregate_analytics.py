from __future__ import annotations

import datetime
import logging
from abc import ABC, abstractmethod
from datetime import UTC
from typing import Any

from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models import (
    Count,
    F,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
)
from django.db.models.fields import DateField
from django.db.models.fields.json import KT
from django.db.models.functions import Cast, TruncDate

from lunes_cms.analytics.models import (
    AnalyticsEvent,
    DropoutAggregate,
    ExerciseRepetitionAggregate,
    JobSelectionAggregate,
    ModuleDurationAggregate,
    SessionAggregate,
)

logger = logging.getLogger(__name__)


class EventAggregator(ABC):
    """
    Base class for event type aggregators.
    Subclasses implement aggregate() to transform raw events into aggregate models.
    """

    event_types: list[str]

    @staticmethod
    @abstractmethod
    def aggregate(events: QuerySet[AnalyticsEvent]) -> None:
        """
        Aggregate the given events into the corresponding aggregate model.
        The queryset is already filtered by event type, bounded by ID,
        and annotated with ``event_date`` (UTC date of the event).
        """


class JobSelectionAggregator(EventAggregator):
    """
    Aggregates job_selected events into daily JobSelectionAggregate records.
    selection_count = number of "add" events minus number of "remove" events.
    """

    event_types = [AnalyticsEvent.EventType.JOB_SELECTED]

    @staticmethod
    def aggregate(events: QuerySet[AnalyticsEvent]) -> None:
        daily_stats = (
            events.annotate(job_id=KT("payload__job_id"))
            .values("job_id", "event_date")
            .annotate(
                selection_count=(
                    Count("id", filter=Q(payload__action="add"))
                    - Count("id", filter=Q(payload__action="remove"))
                ),
            )
        )

        for stat in daily_stats:
            aggregate, _created = JobSelectionAggregate.objects.update_or_create(
                job_id=stat["job_id"],
                date=stat["event_date"],
                defaults={
                    "selection_count": F("selection_count") + stat["selection_count"]
                },
                create_defaults={"selection_count": stat["selection_count"]},
            )
            logger.info("Created or updated aggregate %r", aggregate)


class SessionAggregator(EventAggregator):
    """
    Aggregates session_start and session_end events into daily SessionAggregate records.
    Pairs events by session_id to compute duration, then buckets the durations.
    This command ignores invalid sessions (for example session that have not been completed yet and
    thus only have a session_start, but no session_end event). These invalid or not yet completed sessions
    will be deleted after aggregation.
    Sessions ending on a different day than they started will be attributed to their start day.
    """

    event_types = [
        AnalyticsEvent.EventType.SESSION_START,
        AnalyticsEvent.EventType.SESSION_END,
    ]

    DURATION_BUCKETS: tuple[tuple[str, float], ...] = (
        ("0-1", 1.0),
        ("1-5", 5.0),
        ("5-15", 15.0),
        ("15-30", 30.0),
        ("30-", float("inf")),
    )
    """
    The durations used for the histogram aggregation.
    Values indicate the maximal duration for a given bucket in minutes.
    """

    @classmethod
    def aggregate(cls, events: QuerySet[AnalyticsEvent]) -> None:
        for session in cls.sessions(events):
            date = session["event_date"]
            duration: datetime.timedelta = (
                session["end_timestamp"] - session["timestamp"]
            )
            duration_seconds = duration.total_seconds()
            bucket = cls.get_duration_bucket(duration_seconds / 60)
            aggregate, created = SessionAggregate.objects.update_or_create(
                date=date,
                defaults={
                    "total_sessions": F("total_sessions") + 1,
                    "total_duration_seconds": F("total_duration_seconds")
                    + duration_seconds,
                },
                create_defaults={
                    "total_sessions": 1,
                    "total_duration_seconds": duration_seconds,
                    "duration_buckets": {bucket: 1},
                },
            )
            if not created:
                aggregate.duration_buckets[bucket] = (
                    aggregate.duration_buckets.get(bucket, 0) + 1
                )
                aggregate.save(update_fields=["duration_buckets"])
            logger.info(
                "Created or updated aggregate %r with session %r", aggregate, session
            )

    @classmethod
    def get_duration_bucket(cls, duration_minutes: float) -> str:
        """Returns the duration bucket for the given duration_seconds."""
        for label, max_duration_minutes in cls.DURATION_BUCKETS:
            if duration_minutes <= max_duration_minutes:
                return label
        raise ValueError(f"Invalid value {duration_minutes=}")

    @staticmethod
    def sessions(
        events: QuerySet[AnalyticsEvent],
    ) -> QuerySet[AnalyticsEvent, dict[str, Any]]:
        """
        Converts the query set of session_start and session_end events into a query set of
        valid sessions with `event_date`, `timestamp`, `end_timestamp` and `payload__session_id` keys.
        """
        # First filter on the number of unique session ids.
        # Any session which does not occur exactly twice in the dataset is invalid.
        # For example, a session that was started but not ended, or ended multiple times.
        # This still leaves some invalid data, like sessions that were ended twice or started twice.
        possibly_valid_sessions = (
            events.values("payload__session_id")
            .annotate(num_session_ids=Count("pk"))
            .filter(num_session_ids=2)
            .values("payload__session_id")
        )
        # Next figure out all session end events that may be valid.
        possibly_valid_ends = events.filter(
            event_type=AnalyticsEvent.EventType.SESSION_END,
            payload__session_id__in=possibly_valid_sessions,
        )
        # With the possibly valid ends we can now figure out all the valid pairs of (session_start, session_end):
        # The main condition is: session_id is used exactly twice, there exists an end event with the session id
        # and there exists a start event with the session id. If this is true, we know that the session is valid.
        return (
            events.filter(
                event_type=AnalyticsEvent.EventType.SESSION_START,
            )
            .annotate(
                end_timestamp=Subquery(
                    possibly_valid_ends.filter(
                        payload__session_id=OuterRef("payload__session_id")
                    ).values("timestamp")
                )
            )
            .values("event_date", "timestamp", "end_timestamp", "payload__session_id")
            .filter(end_timestamp__isnull=False)
        )


class ModuleDurationAggregator(EventAggregator):
    """
    Aggregates module duration events.
    """

    event_types = [AnalyticsEvent.EventType.MODULE_DURATION]

    @staticmethod
    def aggregate(events: QuerySet[AnalyticsEvent]) -> None:
        aggregated_events = (
            events.annotate(
                duration_seconds=Cast(
                    KT("payload__duration_seconds"), output_field=IntegerField()
                )
            )
            .values("event_date", "payload__exercise_type", "payload__unit_id")
            .annotate(
                total_duration_seconds=Sum("duration_seconds"),
                total_sessions=Count("pk"),
            )
        )

        for event in aggregated_events:
            aggregate, _created = ModuleDurationAggregate.objects.update_or_create(
                date=event["event_date"],
                exercise_type=event["payload__exercise_type"],
                unit_id=event["payload__unit_id"],
                defaults={
                    "total_duration_seconds": F("total_duration_seconds")
                    + event["total_duration_seconds"],
                    "total_sessions": F("total_sessions") + event["total_sessions"],
                },
                create_defaults={
                    "total_duration_seconds": event["total_duration_seconds"],
                    "total_sessions": event["total_sessions"],
                },
            )
            logger.info("Created or updated aggregate %r", aggregate)


class DropoutAggregator(EventAggregator):
    """
    Aggregates exercise dropout events into daily DropoutAggregate records.
    Groups by (date, exercise_type, unit_id, position, total) and sums dropout counts.
    """

    event_types = [AnalyticsEvent.EventType.EXERCISE_DROPOUT]

    @staticmethod
    def aggregate(events: QuerySet[AnalyticsEvent]) -> None:
        aggregated_events = events.values(
            "event_date",
            "payload__exercise_type",
            "payload__unit_id",
            "payload__position",
            "payload__total",
        ).annotate(
            dropout_count=Count("pk"),
        )

        for event in aggregated_events:
            aggregate, _created = DropoutAggregate.objects.update_or_create(
                date=event["event_date"],
                exercise_type=event["payload__exercise_type"],
                unit_id=event["payload__unit_id"],
                dropout_position=event["payload__position"],
                total_items=event["payload__total"],
                defaults={
                    "dropout_count": F("dropout_count") + event["dropout_count"],
                },
                create_defaults={
                    "dropout_count": event["dropout_count"],
                },
            )
            logger.info("Created or updated aggregate %r", aggregate)


class ExerciseRepetitionAggregator(EventAggregator):
    """
    Aggregates exercise_repetition events into per-session ExerciseRepetitionAggregate records.
    start_count = number of times the same exercise/unit combo was started in a session.
    """

    event_types = [AnalyticsEvent.EventType.EXERCISE_REPETITION]

    @staticmethod
    def aggregate(events: QuerySet[AnalyticsEvent]) -> None:
        aggregated_events = (
            events.annotate(
                _unit_id=Cast(KT("payload__unit_id"), output_field=IntegerField()),
                _exercise_type=KT("payload__exercise_type"),
                _date=Cast(KT("payload__date"), output_field=DateField()),
                _repetition_count=Cast(
                    KT("payload__repetition_count"), output_field=IntegerField()
                ),
                _start_count=Cast(
                    KT("payload__start_count"), output_field=IntegerField()
                ),
            )
            .values("_unit_id", "_exercise_type", "_date")
            .annotate(
                total_repetition_count=Sum("_repetition_count"),
                total_start_count=Sum("_start_count"),
            )
        )

        for stat in aggregated_events:
            aggregate, _ = ExerciseRepetitionAggregate.objects.update_or_create(
                unit_id=stat["_unit_id"],
                exercise_type=stat["_exercise_type"],
                date=stat["_date"],
                defaults={
                    "repetition_count": F("repetition_count")
                    + stat["total_repetition_count"],
                    "start_count": F("start_count") + stat["total_start_count"],
                },
                create_defaults={
                    "repetition_count": stat["total_repetition_count"],
                    "start_count": stat["total_start_count"],
                },
            )
            logger.info("Created or updated aggregate %r", aggregate)


EVENT_AGGREGATORS: list[type[EventAggregator]] = [
    JobSelectionAggregator,
    SessionAggregator,
    ModuleDurationAggregator,
    DropoutAggregator,
    ExerciseRepetitionAggregator,
]


class Command(BaseCommand):
    """
    Aggregate analytics events into daily summaries and delete the raw events.
    """

    help = "Aggregate analytics events into daily summaries and delete the raw events."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the full aggregation pipeline but roll back all changes.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        for aggregator_class in EVENT_AGGREGATORS:
            self._aggregate_event_type(aggregator_class, dry_run)

    @transaction.atomic
    def _aggregate_event_type(
        self,
        aggregator_class: type[EventAggregator],
        dry_run: bool,
    ) -> None:
        event_types = aggregator_class.event_types

        # Capture max ID to avoid deleting events that arrive during aggregation
        max_id = AnalyticsEvent.objects.filter(
            event_type__in=event_types,
        ).aggregate(
            max_id=models.Max("id")
        )["max_id"]

        if max_id is None:
            self.stdout.write(f"No {event_types} events to aggregate.")
            return

        events = AnalyticsEvent.objects.filter(
            event_type__in=event_types,
            id__lte=max_id,
        ).annotate(event_date=TruncDate("timestamp", tzinfo=UTC))

        aggregator_class.aggregate(events)

        count, _ = events.delete()

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(
                f"[DRY RUN] Would aggregate and delete {count} {event_types} events."
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Aggregated and deleted {count} {event_types} events."
                )
            )
