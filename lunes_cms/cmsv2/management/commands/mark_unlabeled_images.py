"""
Management command to mark AI images that lack the AI-disclosure label.

First records the source of every image whose source is still unknown, judged
from its file, then pastes the visible label onto the unlabeled AI images
stored since ``--since`` and embeds the machine-readable marking. A marked
image is stored under a new name, so apps that cache images by URL fetch it
again; the old file is deleted. The check status stays as it is. Uploads are
never touched.

The marked images get their own source, so the "Image source" filter in the
word admin lists them.
"""

from __future__ import annotations

import collections
import datetime
import enum
import logging
import os
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import ImageSource
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.services.image_marking import mark_image
from lunes_cms.cmsv2.services.image_provenance import (
    classify_image,
    image_created_at,
)

logger = logging.getLogger(__name__)

DATE_IMAGE_GENERATION_WAS_ADDED = datetime.date(2025, 6, 23)

MARKED_SUFFIX = "-marked"


class MarkResult(enum.Enum):
    """What happened to one image."""

    MARKED = "marked"
    ALREADY_MARKED = "already marked"
    FAILED = "failed"


def _summary(results: collections.Counter[MarkResult], total: int) -> str:
    summary = f"Marked {results[MarkResult.MARKED]} of {total} image(s)"
    for result in (MarkResult.ALREADY_MARKED, MarkResult.FAILED):
        if results[result]:
            summary += f", {results[result]} {result.value}"
    return summary


def _marked_name(name: str) -> str:
    root, extension = os.path.splitext(name)
    return f"{root}{MARKED_SUFFIX}{extension}"


def _is_referenced(name: str) -> bool:
    return (
        Word.objects.filter(image=name).exists()
        or UnitWordRelation.objects.filter(image=name).exists()
    )


def _describe(instance: Word | UnitWordRelation) -> str:
    if isinstance(instance, UnitWordRelation):
        return f"unit-word #{instance.pk} {instance}"
    return f"word #{instance.pk} {instance.word}"


class Command(BaseCommand):
    """Management command to mark AI images that don't have an AI label yet."""

    help = (
        "Record the source of images stored before it was tracked, then add "
        "the AI-disclosure label and marking to AI-generated images without it."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--since",
            type=datetime.date.fromisoformat,
            default=DATE_IMAGE_GENERATION_WAS_ADDED,
            help=(
                "Only mark images stored on or after this day, as "
                f"YYYY-MM-DD (default: {DATE_IMAGE_GENERATION_WAS_ADDED.isoformat()})"
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of images to mark (default: no limit)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only list what would be recorded and marked",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        since = datetime.datetime.combine(
            options["since"], datetime.time.min, tzinfo=datetime.timezone.utc
        )
        dry_run = options["dry_run"]
        limit = options["limit"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        candidates: list[Word | UnitWordRelation] = []
        for model in (Word, UnitWordRelation):
            candidates += self._record_sources(model, dry_run)

        by_image: dict[str, list[Word | UnitWordRelation]] = {}
        for instance in candidates:
            name = instance.image.name or ""
            created_at = image_created_at(name)
            if created_at and created_at >= since:
                by_image.setdefault(name, []).append(instance)

        self.stdout.write(
            self.style.NOTICE(
                f"{len(by_image)} unlabeled AI image(s) stored since "
                f"{since.date().isoformat()}"
            )
        )
        names = list(by_image)[:limit]

        if dry_run:
            for name in names:
                for instance in by_image[name]:
                    self.stdout.write(f"Would mark {_describe(instance)}")
            return

        results = collections.Counter(
            self._mark_one(name, by_image[name]) for name in names
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{_summary(results, len(names))}. Filter the words by image "
                f'source "{ImageSource.AI_MARKED.label}" to review them.'
            )
        )

    def _mark_one(
        self, name: str, instances: list[Word | UnitWordRelation]
    ) -> MarkResult:
        """
        Mark the image ``name`` shared by ``instances``, store it under a new
        name and delete the old file once nothing uses it.

        Any error is logged and leaves the image as it was.
        """
        storage = instances[0].image.storage
        new_name = _marked_name(name)
        try:
            if mark_image(storage.path(name), storage.path(new_name)):
                self._point_to_image(instances, new_name)
                if not _is_referenced(name):
                    storage.delete(name)
                result = MarkResult.MARKED
            else:
                self._point_to_image(instances, name)
                result = MarkResult.ALREADY_MARKED
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Marking the image %s failed", name)
            return MarkResult.FAILED
        for instance in instances:
            self.stdout.write(f"{result.value.capitalize()} {_describe(instance)}")
        return result

    def _point_to_image(
        self, instances: list[Word | UnitWordRelation], image_name: str
    ) -> None:
        """
        Point ``instances`` at the image ``image_name`` and record them as marked.
        """
        for instance in instances:
            type(instance).objects.filter(pk=instance.pk).update(
                image=image_name, image_source=ImageSource.AI_MARKED
            )

    def _record_sources(
        self, model: type[Word] | type[UnitWordRelation], dry_run: bool
    ) -> list[Word | UnitWordRelation]:
        """
        Record the source of every image of ``model`` whose source is unknown,
        and return all instances with an unlabeled AI image.
        """
        unlabeled: list[Word | UnitWordRelation] = list(
            model.objects.filter(image_source=ImageSource.AI_UNLABELED)
            .exclude(image="")
            .order_by("pk")
        )
        counts: dict[str, int] = {}
        unknown = (
            model.objects.filter(image_source=ImageSource.UNKNOWN)
            .exclude(image="")
            .exclude(image__isnull=True)
            .order_by("pk")
        )
        for instance in unknown.iterator():
            source = classify_image(instance.image)
            source_label = str(source.label) if source else "unreadable"
            counts[source_label] = counts.get(source_label, 0) + 1
            if source is None:
                continue
            if not dry_run:
                model.objects.filter(pk=instance.pk).update(image_source=source)
            if source == ImageSource.AI_UNLABELED:
                unlabeled.append(instance)
        summary = (
            ", ".join(f"{source_label}: {n}" for source_label, n in counts.items())
            or "none"
        )
        self.stdout.write(
            f"{model._meta.verbose_name_plural}, "  # pylint: disable=protected-access
            f"recorded image sources: {summary}"
        )
        return unlabeled
