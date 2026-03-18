from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC

from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models import Count, F, Q, QuerySet
from django.db.models.fields.json import KT
from django.db.models.functions import TruncDate

from lunes_cms.analytics.models import AnalyticsEvent, JobSelectionAggregate

logger = logging.getLogger(__name__)


class EventAggregator(ABC):
    """
    Base class for event type aggregators.
    Subclasses implement aggregate() to transform raw events into aggregate models.
    """

    event_type: str

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

    event_type = AnalyticsEvent.EventType.JOB_SELECTED

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
            logger.info(f"Created or updated aggregate %r", aggregate)


EVENT_AGGREGATORS: list[type[EventAggregator]] = [
    JobSelectionAggregator,
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
        event_type = aggregator_class.event_type

        # Capture max ID to avoid deleting events that arrive during aggregation
        max_id = AnalyticsEvent.objects.filter(
            event_type=event_type,
        ).aggregate(
            max_id=models.Max("id")
        )["max_id"]

        if max_id is None:
            self.stdout.write(f"No {event_type} events to aggregate.")
            return

        events = AnalyticsEvent.objects.filter(
            event_type=event_type,
            id__lte=max_id,
        ).annotate(event_date=TruncDate("timestamp", tzinfo=UTC))

        aggregator_class.aggregate(events)

        count, _ = events.delete()

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(
                f"[DRY RUN] Would aggregate and delete {count} {event_type} events."
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Aggregated and deleted {count} {event_type} events."
                )
            )
