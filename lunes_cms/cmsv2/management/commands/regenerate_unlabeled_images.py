"""
Management command to regenerate AI images that lack the AI-disclosure label.

Images generated before the label was added to the prompt (issue #936) do not
carry it, although the EU AI Act (Art. 50) requires generated images to be
marked. This command first records the source of every image whose source is
still unknown, judged from its file, and then regenerates the unlabeled AI
images stored since ``--since``. Uploads are never touched.

The check status of a regenerated image is kept, so the regenerated images are
marked with their own source instead: the "Image source" filter in the word
admin lists them for review.
"""

from __future__ import annotations

import datetime
import logging
import time
from typing import Any, TYPE_CHECKING

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError, CommandParser
from openai import RateLimitError

from lunes_cms.cmsv2.models import Job, Word
from lunes_cms.cmsv2.models.static import ImageSource
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.services.image_generation import (
    build_image_prompt,
    GENERATED_IMAGE_EXTENSION,
    openai_image_bytes,
)
from lunes_cms.cmsv2.services.image_provenance import (
    classify_image,
    image_created_at,
)
from lunes_cms.cmsv2.utils import OpenAIConfigurationError

if TYPE_CHECKING:
    from django.db.models import QuerySet

logger = logging.getLogger(__name__)

#: Images stored before this day are left alone by default.
DEFAULT_SINCE = datetime.date(2026, 8, 2)

#: Seconds to wait before retrying after OpenAI's rate limit was hit.
RATE_LIMIT_BACKOFF = 30


def _single_job_title(jobs: QuerySet[Job]) -> str | None:
    """
    Return the name of the only job in ``jobs``, same as the admin does when it
    adds the job to a prompt, or None if there are none or several.
    """
    # Fetching 2 is enough to tell "exactly one" from "more than one".
    first_two = list(jobs.distinct()[:2])
    return first_two[0].name if len(first_two) == 1 else None


def _prompt_for(instance: Word | UnitWordRelation) -> str:
    """
    Build the prompt the admin would use to generate this image.

    Editor hints and the text permission of the original generation were never
    stored, so the prompt is the default one for the word.
    """
    if isinstance(instance, UnitWordRelation):
        return build_image_prompt(
            instance.word.word,
            unit_title=instance.unit.title,
            job_title=_single_job_title(instance.unit.jobs.all()),
        )
    return build_image_prompt(
        instance.word,
        job_title=_single_job_title(
            Job.objects.filter(units__unit_word_relations__word=instance)
        ),
    )


def _is_referenced(name: str) -> bool:
    """
    Check whether any Word or UnitWordRelation still uses the image ``name``.
    """
    return (
        Word.objects.filter(image=name).exists()
        or UnitWordRelation.objects.filter(image=name).exists()
    )


def _describe(instance: Word | UnitWordRelation) -> str:
    if isinstance(instance, UnitWordRelation):
        return f"unit-word #{instance.pk} {instance}"
    return f"word #{instance.pk} {instance.word}"


class Command(BaseCommand):
    """Management command to regenerate AI images without the AI label."""

    help = (
        "Record the source of images stored before it was tracked, then "
        "regenerate AI-generated images that lack the AI-disclosure label."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--since",
            type=datetime.date.fromisoformat,
            default=DEFAULT_SINCE,
            help=(
                "Only regenerate images stored on or after this day, as "
                f"YYYY-MM-DD (default: {DEFAULT_SINCE.isoformat()})"
            ),
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Delay in seconds between two generated images (default: 1.0)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of images to regenerate (default: no limit)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only list what would be recorded and regenerated",
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
            candidates += self._classify(model, dry_run)
        candidates = [
            instance
            for instance in candidates
            if (created := image_created_at(instance.image.name or ""))
            and created >= since
        ]
        self.stdout.write(
            self.style.NOTICE(
                f"{len(candidates)} unlabeled AI image(s) stored since "
                f"{since.date().isoformat()}"
            )
        )
        if limit is not None:
            candidates = candidates[:limit]

        if dry_run:
            for instance in candidates:
                self.stdout.write(f"Would regenerate {_describe(instance)}")
            return

        regenerated = 0
        for instance in candidates:
            if self._regenerate(instance):
                regenerated += 1
                self.stdout.write(f"Regenerated {_describe(instance)}")
            time.sleep(options["delay"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Regenerated {regenerated} of {len(candidates)} image(s). "
                "Filter the words by image source "
                f'"{ImageSource.AI_RELABELED.label}" to review them.'
            )
        )

    def _classify(
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
            label = str(source.label) if source else "unreadable"
            counts[label] = counts.get(label, 0) + 1
            if source is None:
                continue
            if not dry_run:
                model.objects.filter(pk=instance.pk).update(image_source=source)
            if source == ImageSource.AI_UNLABELED:
                instance.image_source = source
                unlabeled.append(instance)
        summary = ", ".join(f"{label}: {n}" for label, n in counts.items()) or "none"
        self.stdout.write(
            f"{model._meta.verbose_name_plural}, "  # pylint: disable=protected-access
            f"recorded image sources: {summary}"
        )
        return unlabeled

    def _regenerate(self, instance: Word | UnitWordRelation) -> bool:
        """
        Replace the image of ``instance`` with a newly generated, labeled one,
        keeping its check status.

        Returns True on success. Aborts the command if OpenAI is not configured.
        """
        prompt = _prompt_for(instance)
        while True:
            try:
                data = openai_image_bytes(prompt)
                break
            except OpenAIConfigurationError as e:
                raise CommandError(str(e)) from e
            except RateLimitError:
                logger.warning("OpenAI rate limit, backing off %ss", RATE_LIMIT_BACKOFF)
                time.sleep(RATE_LIMIT_BACKOFF)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception(
                    "Generating an image for %s failed", _describe(instance)
                )
                return False

        old_image = instance.image.name
        check_status = instance.image_check_status
        storage = instance.image.storage
        # The extension has to match OpenAI's encode, or saving re-encodes the
        # file and strips its provenance markings.
        instance.image.save(
            f"image{GENERATED_IMAGE_EXTENSION}", ContentFile(data), save=False
        )
        instance.save(image_source=ImageSource.AI_RELABELED)
        # Saving a new image resets its check status; the regenerated images are
        # tracked by their source instead.
        type(instance).objects.filter(pk=instance.pk).update(
            image_check_status=check_status
        )
        instance.image_check_status = check_status
        if old_image and not _is_referenced(old_image):
            storage.delete(old_image)
        return True
