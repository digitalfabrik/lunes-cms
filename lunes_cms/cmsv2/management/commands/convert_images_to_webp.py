"""
Management command to convert existing images to WebP format.

"""

import logging

from django.core.management.base import BaseCommand

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import convert_image_to_webp
from lunes_cms.cmsv2.models.unit import UnitWordRelation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command to convert existing images to WebP format."""

    help = "Convert existing images to WebP format for Word and UnitWordRelation instances."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show which items would be processed without actually converting images",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of items to process (default: no limit)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        self.stdout.write(self.style.NOTICE("Starting image conversion to WebP..."))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        total_processed = self._process_words(dry_run, limit)

        remaining_limit = None if limit is None else max(0, limit - total_processed)
        if remaining_limit is None or remaining_limit > 0:
            total_processed += self._process_unit_word_relations(
                dry_run, remaining_limit
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Conversion complete. Total processed: {total_processed}"
            )
        )

    def _process_words(self, dry_run, limit):
        """Process Word instances."""
        self.stdout.write(self.style.NOTICE("Processing words..."))

        queryset = (
            Word.objects.filter(image__isnull=False)
            .exclude(image="")
            .exclude(image__endswith=".webp")
        )

        if limit is not None:
            queryset = queryset[:limit]

        processed_count = 0
        for word in queryset:
            logger.info("Processing word #%d: %s", word.pk, word.word)

            if dry_run:
                logger.info(
                    "[DRY RUN] Would convert image for word: %s (%s)",
                    word.word,
                    word.image.name,
                )
                processed_count += 1
            else:
                if self._convert_image(word, label=f"word #{word.pk}: {word.word}"):
                    processed_count += 1

        logger.info("Finished processing words. Count: %d", processed_count)
        return processed_count

    def _process_unit_word_relations(self, dry_run, limit):
        """Process UnitWordRelation instances."""
        self.stdout.write(self.style.NOTICE("Processing unit-word relations..."))

        queryset = (
            UnitWordRelation.objects.filter(image__isnull=False)
            .exclude(image="")
            .exclude(image__endswith=".webp")
        )

        if limit is not None:
            queryset = queryset[:limit]

        processed_count = 0
        for unitword in queryset:
            word_text = unitword.word.word
            unit_title = unitword.unit.title
            logger.info(
                "Processing unit-word #%d: %s in %s",
                unitword.pk,
                word_text,
                unit_title,
            )

            if dry_run:
                logger.info(
                    "[DRY RUN] Would convert image for unit-word: %s in %s (%s)",
                    word_text,
                    unit_title,
                    unitword.image.name,
                )
                processed_count += 1
            else:
                if self._convert_image(
                    unitword,
                    label=f"unit-word #{unitword.pk}: {word_text} in {unit_title}",
                ):
                    processed_count += 1

        logger.info(
            "Finished processing unit-word relations. Count: %d", processed_count
        )
        return processed_count

    def _convert_image(self, instance, label):
        """
        Convert the image of a Word or UnitWordRelation instance to WebP.

        Args:
            instance: The Word or UnitWordRelation instance to process.
            label: A human-readable label for logging.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if convert_image_to_webp(instance.image):
                instance.save(update_fields=["image"])
                logger.info("Successfully converted image for %s", label)
                return True
            logger.warning("Image already WebP or skipped for %s", label)
            return False
        except (OSError, ValueError) as e:
            logger.error("Error converting image for %s: %s", label, e)
            return False
