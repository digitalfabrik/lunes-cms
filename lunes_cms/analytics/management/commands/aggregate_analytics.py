from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models import (
    Count,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
)
from django.db.models.fields.json import KT
from django.db.models.functions import Cast, TruncDate
from django.utils import timezone

from lunes_cms.analytics.influx import date_to_ns, push_lines, resolve_job, resolve_unit
from lunes_cms.analytics.models import AnalyticsEvent
from lunes_cms.cmsv2.models import Job, Unit

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90


class EventAggregator(ABC):
    """
    Base class for event type aggregators.
    Subclasses implement aggregate() to transform raw events into InfluxDB line
    protocol strings and to mark the consumed events with ``aggregated_at`` so
    they are not picked up on subsequent runs.
    """

    event_types: list[str]

    @staticmethod
    @abstractmethod
    def aggregate(
        events: QuerySet[AnalyticsEvent],
        aggregated_at: datetime,
        job_names: dict[int, str],
        unit_names: dict[int, str],
    ) -> list[str]:
        """
        Aggregate the given events into InfluxDB line protocol strings and mark
        the events that were consumed by setting ``aggregated_at``.

        The queryset is already filtered to events of this aggregator's types,
        bounded by the snapshot ID, restricted to ``aggregated_at__isnull=True``
        and annotated with ``event_date`` (UTC date of the event).

        Returns a list of InfluxDB line protocol strings to be pushed after the
        transaction commits.
        """


class JobSelectionAggregator(EventAggregator):
    """
    Aggregates job_selected events into daily lunes_job_selection measurements.
    selection_count = number of "add" events minus number of "remove" events.
    """

    event_types = [AnalyticsEvent.EventType.JOB_SELECTED]

    @staticmethod
    def aggregate(
        events: QuerySet[AnalyticsEvent],
        aggregated_at: datetime,
        job_names: dict[int, str],
        unit_names: dict[int, str],
    ) -> list[str]:
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

        lines = []
        for stat in daily_stats:
            job_id = stat["job_id"]
            job_name = resolve_job(job_id, job_names)
            if job_name is None:
                logger.warning("job_selected event has no job_id, skipping")
                continue
            ts = date_to_ns(stat["event_date"])
            lines.append(
                f"lunes_job_selection,job_id={job_id}"
                f" job_name=\"{job_name}\",selection_count={stat['selection_count']}i {ts}"
            )
            logger.info(
                "Queued job_selection line: job_id=%s date=%s count=%d",
                job_id,
                stat["event_date"],
                stat["selection_count"],
            )

        events.update(aggregated_at=aggregated_at)
        return lines


class SessionAggregator(EventAggregator):
    """
    Aggregates session_start and session_end events into daily lunes_sessions
    measurements. Pairs events by session_id to compute duration.

    Sessions whose start and end fall on different UTC days are attributed to
    their start day. Sessions that cannot be paired in this run (for example a
    session_start whose session_end has not arrived yet, or a session_id that
    appears more than twice) are left unmarked so a later run can pick them up
    once the matching event arrives.
    """

    event_types = [
        AnalyticsEvent.EventType.SESSION_START,
        AnalyticsEvent.EventType.SESSION_END,
    ]

    @classmethod
    def aggregate(
        cls,
        events: QuerySet[AnalyticsEvent],
        aggregated_at: datetime,
        job_names: dict[int, str],
        unit_names: dict[int, str],
    ) -> list[str]:
        # Accumulate per-date totals in Python before building lines
        daily: dict[Any, tuple[int, int]] = (
            {}
        )  # event_date -> (session_count, total_duration_seconds)
        consumed_session_ids: list[str] = []

        for session in cls.sessions(events):
            d = session["event_date"]
            duration_seconds = int(
                (session["end_timestamp"] - session["timestamp"]).total_seconds()
            )
            count, total = daily.get(d, (0, 0))
            daily[d] = (count + 1, total + duration_seconds)
            consumed_session_ids.append(session["payload__session_id"])
            logger.info("Queued session for date=%s duration=%ds", d, duration_seconds)

        lines = []
        for d, (count, total_duration) in daily.items():
            ts = date_to_ns(d)
            lines.append(
                f"lunes_sessions total_sessions={count}i,total_duration_seconds={total_duration}i {ts}"
            )

        if consumed_session_ids:
            events.filter(payload__session_id__in=consumed_session_ids).update(
                aggregated_at=aggregated_at
            )
        return lines

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
    Aggregates module duration events into daily lunes_module_duration measurements
    for both standard (unit-based) and training (job-based) exercises.
    """

    event_types = [AnalyticsEvent.EventType.MODULE_DURATION]

    @staticmethod
    def aggregate(
        events: QuerySet[AnalyticsEvent],
        aggregated_at: datetime,
        job_names: dict[int, str],
        unit_names: dict[int, str],
    ) -> list[str]:
        standard_events = events.filter(
            payload__exercise_key__type=AnalyticsEvent.ExerciseKeyType.STANDARD
        )
        training_events = events.filter(
            payload__exercise_key__type=AnalyticsEvent.ExerciseKeyType.TRAINING
        )

        lines = []

        standard_aggregated = (
            standard_events.annotate(
                exercise_type=KT("payload__exercise_key__exercise_type"),
                unit_id=KT("payload__exercise_key__unit_id"),
                duration_seconds=Cast(
                    KT("payload__duration_seconds"), output_field=IntegerField()
                ),
            )
            .values("event_date", "exercise_type", "unit_id")
            .annotate(
                total_duration_seconds=Sum("duration_seconds"),
                total_sessions=Count("pk"),
            )
        )
        for event in standard_aggregated:
            unit_id = event["unit_id"]
            unit_name = resolve_unit(unit_id, unit_names)
            if unit_name is None:
                logger.warning(
                    "module_duration standard event has no unit_id, skipping"
                )
                continue
            ts = date_to_ns(event["event_date"])
            lines.append(
                f"lunes_module_duration,unit_id={unit_id},exercise_type={event['exercise_type']}"
                f" unit_name=\"{unit_name}\",total_sessions={event['total_sessions']}i,total_duration_seconds={event['total_duration_seconds']}i {ts}"
            )
            logger.info(
                "Queued module_duration (standard) line: unit_id=%s exercise_type=%s date=%s",
                unit_id,
                event["exercise_type"],
                event["event_date"],
            )

        training_aggregated = (
            training_events.annotate(
                exercise_type=KT("payload__exercise_key__exercise_type"),
                job_id=KT("payload__exercise_key__job_id"),
                duration_seconds=Cast(
                    KT("payload__duration_seconds"), output_field=IntegerField()
                ),
            )
            .values("event_date", "exercise_type", "job_id")
            .annotate(
                total_duration_seconds=Sum("duration_seconds"),
                total_sessions=Count("pk"),
            )
        )
        for event in training_aggregated:
            job_id = event["job_id"]
            job_name = resolve_job(job_id, job_names)
            if job_name is None:
                logger.warning("module_duration training event has no job_id, skipping")
                continue
            ts = date_to_ns(event["event_date"])
            lines.append(
                f"lunes_module_duration,job_id={job_id},exercise_type={event['exercise_type']}"
                f" job_name=\"{job_name}\",total_sessions={event['total_sessions']}i,total_duration_seconds={event['total_duration_seconds']}i {ts}"
            )
            logger.info(
                "Queued module_duration (training) line: job_id=%s exercise_type=%s date=%s",
                job_id,
                event["exercise_type"],
                event["event_date"],
            )

        events.update(aggregated_at=aggregated_at)
        return lines


class DropoutAggregator(EventAggregator):
    """
    Aggregates exercise dropout events into daily lunes_dropout measurements
    for both standard and training exercises.
    """

    event_types = [AnalyticsEvent.EventType.EXERCISE_DROPOUT]

    @staticmethod
    def aggregate(
        events: QuerySet[AnalyticsEvent],
        aggregated_at: datetime,
        job_names: dict[int, str],
        unit_names: dict[int, str],
    ) -> list[str]:
        standard_events = events.filter(
            payload__exercise_key__type=AnalyticsEvent.ExerciseKeyType.STANDARD
        )
        training_events = events.filter(
            payload__exercise_key__type=AnalyticsEvent.ExerciseKeyType.TRAINING
        )

        lines = []

        standard_aggregated = (
            standard_events.annotate(
                exercise_type=KT("payload__exercise_key__exercise_type"),
                unit_id=KT("payload__exercise_key__unit_id"),
            )
            .values(
                "event_date",
                "exercise_type",
                "unit_id",
                "payload__position",
                "payload__total",
            )
            .annotate(dropout_count=Count("pk"))
        )
        for event in standard_aggregated:
            unit_id = event["unit_id"]
            unit_name = resolve_unit(unit_id, unit_names)
            if unit_name is None:
                logger.warning("dropout standard event has no unit_id, skipping")
                continue
            ts = date_to_ns(event["event_date"])
            lines.append(
                f"lunes_dropout"
                f",unit_id={unit_id}"
                f",exercise_type={event['exercise_type']}"
                f",position={event['payload__position']}"
                f",total={event['payload__total']}"
                f" unit_name=\"{unit_name}\",dropout_count={event['dropout_count']}i {ts}"
            )
            logger.info(
                "Queued dropout (standard) line: unit_id=%s exercise_type=%s date=%s",
                unit_id,
                event["exercise_type"],
                event["event_date"],
            )

        training_aggregated = (
            training_events.annotate(
                exercise_type=KT("payload__exercise_key__exercise_type"),
                job_id=KT("payload__exercise_key__job_id"),
            )
            .values(
                "event_date",
                "exercise_type",
                "job_id",
                "payload__position",
                "payload__total",
            )
            .annotate(dropout_count=Count("pk"))
        )
        for event in training_aggregated:
            job_id = event["job_id"]
            job_name = resolve_job(job_id, job_names)
            if job_name is None:
                logger.warning("dropout training event has no job_id, skipping")
                continue
            ts = date_to_ns(event["event_date"])
            lines.append(
                f"lunes_dropout"
                f",job_id={job_id}"
                f",exercise_type={event['exercise_type']}"
                f",position={event['payload__position']}"
                f",total={event['payload__total']}"
                f" job_name=\"{job_name}\",dropout_count={event['dropout_count']}i {ts}"
            )
            logger.info(
                "Queued dropout (training) line: job_id=%s exercise_type=%s date=%s",
                job_id,
                event["exercise_type"],
                event["event_date"],
            )

        events.update(aggregated_at=aggregated_at)
        return lines


class ExerciseRepetitionAggregator(EventAggregator):
    """
    Aggregates exercise_repetition events into a daily histogram per exercise:
    for each (day, exercise, repetitions_per_session) bucket, reports how many sessions
    landed there. This preserves the per-session difficulty signal (one user grinding an
    exercise 5 times vs. five users doing it once) without storing session_id in InfluxDB.
    """

    event_types = [AnalyticsEvent.EventType.EXERCISE_REPETITION]

    @staticmethod
    def aggregate(
        events: QuerySet[AnalyticsEvent],
        aggregated_at: datetime,
        job_names: dict[int, str],
        unit_names: dict[int, str],
    ) -> list[str]:
        standard_events = events.filter(
            payload__exercise_key__type=AnalyticsEvent.ExerciseKeyType.STANDARD
        )
        training_events = events.filter(
            payload__exercise_key__type=AnalyticsEvent.ExerciseKeyType.TRAINING
        )
        lines = ExerciseRepetitionAggregator._standard_lines(
            standard_events, unit_names
        ) + ExerciseRepetitionAggregator._training_lines(training_events, job_names)
        events.update(aggregated_at=aggregated_at)
        return lines

    @staticmethod
    def _standard_lines(
        standard_events: QuerySet[AnalyticsEvent], unit_names: dict[int, str]
    ) -> list[str]:
        per_session = (
            standard_events.annotate(
                exercise_type=KT("payload__exercise_key__exercise_type"),
                unit_id=KT("payload__exercise_key__unit_id"),
                session_id=KT("payload__session_id"),
            )
            .values("event_date", "exercise_type", "unit_id", "session_id")
            .annotate(reps=Count("pk"))
        )
        dist: dict[tuple, int] = {}
        unit_name_cache: dict[str, str] = {}
        for row in per_session:
            unit_id = row["unit_id"]
            unit_name = resolve_unit(unit_id, unit_names)
            if unit_name is None:
                logger.warning(
                    "exercise_repetition standard event has no unit_id, skipping"
                )
                continue
            unit_name_cache[unit_id] = unit_name
            key = (row["event_date"], row["exercise_type"], unit_id, row["reps"])
            dist[key] = dist.get(key, 0) + 1
        lines = []
        for (event_date, exercise_type, unit_id, reps), session_count in dist.items():
            ts = date_to_ns(event_date)
            lines.append(
                f"lunes_exercise_repetition"
                f",unit_id={unit_id}"
                f",exercise_type={exercise_type}"
                f",repetitions_per_session={reps}"
                f' unit_name="{unit_name_cache[unit_id]}",session_count={session_count}i {ts}'
            )
            logger.info(
                "Queued exercise_repetition (standard) line: unit_id=%s exercise_type=%s reps=%d date=%s",
                unit_id,
                exercise_type,
                reps,
                event_date,
            )
        return lines

    @staticmethod
    def _training_lines(
        training_events: QuerySet[AnalyticsEvent], job_names: dict[int, str]
    ) -> list[str]:
        per_session = (
            training_events.annotate(
                exercise_type=KT("payload__exercise_key__exercise_type"),
                job_id=KT("payload__exercise_key__job_id"),
                session_id=KT("payload__session_id"),
            )
            .values("event_date", "exercise_type", "job_id", "session_id")
            .annotate(reps=Count("pk"))
        )
        dist: dict[tuple, int] = {}
        job_name_cache: dict[str, str] = {}
        for row in per_session:
            job_id = row["job_id"]
            job_name = resolve_job(job_id, job_names)
            if job_name is None:
                logger.warning(
                    "exercise_repetition training event has no job_id, skipping"
                )
                continue
            job_name_cache[job_id] = job_name
            key = (row["event_date"], job_id, row["exercise_type"], row["reps"])
            dist[key] = dist.get(key, 0) + 1
        lines = []
        for (event_date, job_id, exercise_type, reps), session_count in dist.items():
            ts = date_to_ns(event_date)
            lines.append(
                f"lunes_exercise_repetition"
                f",job_id={job_id}"
                f",exercise_type={exercise_type}"
                f",repetitions_per_session={reps}"
                f' job_name="{job_name_cache[job_id]}",session_count={session_count}i {ts}'
            )
            logger.info(
                "Queued exercise_repetition (training) line: job_id=%s exercise_type=%s reps=%d date=%s",
                job_id,
                exercise_type,
                reps,
                event_date,
            )
        return lines


EVENT_AGGREGATORS: list[type[EventAggregator]] = [
    JobSelectionAggregator,
    SessionAggregator,
    ModuleDurationAggregator,
    DropoutAggregator,
    ExerciseRepetitionAggregator,
]


class Command(BaseCommand):
    """
    Aggregate analytics events and push daily summaries to InfluxDB.

    Raw events are kept after aggregation; each consumed event is stamped with
    ``aggregated_at`` so subsequent runs only process newly arrived events.
    """

    help = "Aggregate analytics events and push daily summaries to InfluxDB (raw events are retained)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the full aggregation pipeline but roll back all DB changes and skip InfluxDB push.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        job_names: dict[int, str] = dict(Job.objects.values_list("id", "name"))
        unit_names: dict[int, str] = dict(Unit.objects.values_list("id", "title"))
        for aggregator_class in EVENT_AGGREGATORS:
            self._aggregate_event_type(aggregator_class, dry_run, job_names, unit_names)

    # Will be uncommented with #829
    # self._delete_old_unprocessed_events(dry_run)

    @transaction.atomic
    def _delete_old_unprocessed_events(self, dry_run: bool) -> None:
        """
        Delete events not covered by any batch aggregator that are older than RETENTION_DAYS.

        This includes exercise_repetition events (aggregated inline on receipt)
        and any unknown event types.

        We exclude batch aggregator event types from this deletion for security reasons to avoid data loss.
        For example someone removes atomic transaction annotation and aggregation fails.
        """
        batch_aggregated_types = [
            event_type
            for aggregator in EVENT_AGGREGATORS
            for event_type in aggregator.event_types
        ]
        cutoff = datetime.now(tz=UTC) - timedelta(days=RETENTION_DAYS)
        old_events = AnalyticsEvent.objects.filter(timestamp__lt=cutoff).exclude(
            event_type__in=batch_aggregated_types
        )
        count, _ = old_events.delete()

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(
                f"[DRY RUN] Would delete {count} unprocessed events older than {RETENTION_DAYS} days."
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {count} unprocessed events older than {RETENTION_DAYS} days."
                )
            )

    @transaction.atomic
    def _aggregate_event_type(
        self,
        aggregator_class: type[EventAggregator],
        dry_run: bool,
        job_names: dict[int, str],
        unit_names: dict[int, str],
    ) -> None:
        event_types = aggregator_class.event_types

        # Capture max ID to avoid touching events that arrive during aggregation.
        max_id = AnalyticsEvent.objects.filter(
            event_type__in=event_types,
            aggregated_at__isnull=True,
        ).aggregate(max_id=models.Max("id"))["max_id"]

        if max_id is None:
            self.stdout.write(f"No new {event_types} events to aggregate.")
            return

        events = AnalyticsEvent.objects.filter(
            event_type__in=event_types,
            aggregated_at__isnull=True,
            id__lte=max_id,
        ).annotate(event_date=TruncDate("timestamp", tzinfo=UTC))

        aggregated_at = timezone.now()
        lines = aggregator_class.aggregate(events, aggregated_at, job_names, unit_names)

        marked_count = AnalyticsEvent.objects.filter(
            event_type__in=event_types,
            aggregated_at=aggregated_at,
        ).count()

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(
                f"[DRY RUN] Would aggregate and mark {marked_count} {event_types} events "
                f"({len(lines)} InfluxDB lines skipped)."
            )
        else:
            # Push after the transaction commits so we only push data that was successfully marked.
            if lines:
                transaction.on_commit(lambda: push_lines(lines))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Aggregated and marked {marked_count} {event_types} events "
                    f"({len(lines)} InfluxDB lines queued)."
                )
            )
