"""
Management command to regenerate example sentence audio using the new TTS model.

This command processes words and unit-word relations one at a time, regenerating
their example sentence audio with the gpt-4o-mini-tts model which supports
instructions for proper intonation.
"""

import logging
import time

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.utils import get_openai_client, OpenAIConfigurationError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command to regenerate example sentence audio."""

    help = (
        "Regenerate example sentence audio for words and unit-word relations "
        "using the new TTS model with proper intonation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Delay in seconds between processing each item (default: 1.0)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show which items would be processed without actually regenerating audio",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of items to process (default: no limit)",
        )

    def handle(self, *args, **options):
        delay = options["delay"]
        dry_run = options["dry_run"]
        limit = options["limit"]

        self.stdout.write(
            self.style.NOTICE("Starting example sentence audio regeneration...")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        total_processed = self._process_words(delay, dry_run, limit)

        remaining_limit = None if limit is None else max(0, limit - total_processed)
        if remaining_limit is None or remaining_limit > 0:
            total_processed += self._process_unit_word_relations(
                delay, dry_run, remaining_limit
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Regeneration complete. Total processed: {total_processed}"
            )
        )

    def _process_words(self, delay, dry_run, limit):
        """Process Word instances."""
        self.stdout.write(self.style.NOTICE("Processing words..."))
        processed_count = 0

        while True:
            word = (
                Word.objects.filter(
                    example_sentence_audio_regenerated=False,
                    example_sentence__isnull=False,
                )
                .exclude(example_sentence="")
                .exclude(example_sentence_audio="")
                .exclude(example_sentence_audio__isnull=True)
                .first()
            )

            if word is None:
                logger.info("No more words to process.")
                break

            if limit is not None and processed_count >= limit:
                logger.info("Reached limit of %d words.", limit)
                break

            logger.info("Processing word #%d: %s", word.pk, word.word)

            if dry_run:
                logger.info(
                    "[DRY RUN] Would regenerate audio for word: %s - Example: %s...",
                    word.word,
                    word.example_sentence[:50],
                )
            else:
                success = self._regenerate_audio(
                    instance=word,
                    example_sentence=word.example_sentence,
                    filename=f'{word.word.replace(" ", "_")}_example_sentence.mp3',
                )
                if success:
                    processed_count += 1
                    logger.info(
                        "Successfully regenerated audio for word #%d: %s",
                        word.pk,
                        word.word,
                    )
                else:
                    logger.error(
                        "Failed to regenerate audio for word #%d: %s",
                        word.pk,
                        word.word,
                    )

            time.sleep(delay)

        logger.info("Finished processing words. Count: %d", processed_count)
        return processed_count

    def _process_unit_word_relations(self, delay, dry_run, limit):
        """Process UnitWordRelation instances."""
        self.stdout.write(self.style.NOTICE("Processing unit-word relations..."))
        processed_count = 0

        while True:
            unitword = (
                UnitWordRelation.objects.filter(
                    example_sentence_audio_regenerated=False,
                    example_sentence__isnull=False,
                )
                .exclude(example_sentence="")
                .exclude(example_sentence_audio="")
                .exclude(example_sentence_audio__isnull=True)
                .first()
            )

            if unitword is None:
                logger.info("No more unit-word relations to process.")
                break

            if limit is not None and processed_count >= limit:
                logger.info("Reached limit of %d unit-word relations.", limit)
                break

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
                    "[DRY RUN] Would regenerate audio for unit-word: %s - Example: %s...",
                    word_text,
                    unitword.example_sentence[:50],
                )
            else:
                success = self._regenerate_audio(
                    instance=unitword,
                    example_sentence=unitword.example_sentence,
                    filename=f'{word_text.replace(" ", "_")}_{unit_title.replace(" ", "_")}_example_sentence.mp3',
                )
                if success:
                    processed_count += 1
                    logger.info(
                        "Successfully regenerated audio for unit-word #%d", unitword.pk
                    )
                else:
                    logger.error(
                        "Failed to regenerate audio for unit-word #%d", unitword.pk
                    )

            time.sleep(delay)

        logger.info(
            "Finished processing unit-word relations. Count: %d", processed_count
        )
        return processed_count

    def _regenerate_audio(self, instance, example_sentence, filename):
        """
        Regenerate the example sentence audio for a Word or UnitWordRelation.

        Args:
            instance: The Word or UnitWordRelation instance to process.
            example_sentence: The example sentence text.
            filename: The filename for the audio file.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            client = get_openai_client()

            # Determine instruction based on sentence ending
            if example_sentence.strip().endswith("?"):
                instruction = "Read this sentence as a question with rising intonation."
            else:
                instruction = "Read this sentence as a declarative statement with neutral, falling intonation."

            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="nova",
                input=example_sentence,
                instructions=instruction,
            )

            # Read the audio content
            audio_content = b""
            for chunk in response.iter_bytes(chunk_size=4096):
                audio_content += chunk

            content_file = ContentFile(audio_content, name=filename)

            # Delete old audio file if exists
            if instance.example_sentence_audio:
                instance.example_sentence_audio.delete(save=False)

            # Save new audio
            instance.example_sentence_audio.save(content_file.name, content_file)
            instance.example_sentence_audio_regenerated = True
            instance.save(
                update_fields=[
                    "example_sentence_audio",
                    "example_sentence_audio_regenerated",
                ]
            )

            return True

        except OpenAIConfigurationError as e:
            logger.error("OpenAI configuration error: %s", e)
            return False
        except (ValueError, ConnectionError, TimeoutError) as e:
            logger.error("Error regenerating audio: %s", e)
            return False
