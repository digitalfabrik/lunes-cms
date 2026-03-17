import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from django.utils.translation import gettext_lazy as _
from tablib import Dataset

from ..models import Job, Static, Unit, Word

logger = logging.getLogger(__name__)


COLUMN_MAPPING: dict[str, str] = {
    "Einheit": "unit",
    "Sinneinheit": "unit",
    "Sinneseinheit": "unit",
    "Fachbegriff": "word",
    "Begriff": "word",
    "Vokabel": "word",
    "Artikel": "article",
    "Beispielsatz": "example",
}


@dataclass(frozen=True)
class ParsedRow:
    """
    Cleaned data for a single row
    """

    unit: str
    word: str
    article: str
    example: str = ""


class InvalidRowError(ValueError):
    """
    Error for rows that are invalid
    """

    pass  # pylint: disable=unnecessary-pass


@dataclass
class RowResult:
    """
    Return object of a single row.
    """

    created: int = 0
    updated: int = 0
    error: Optional[str] = None


def map_article_to_int(article: str) -> int:
    """
    Converts article string to article int in DB.
    """
    ARTICLE_MAP: dict[str, int] = {
        label.lower(): value for value, label in Static.singular_article_choices
    } | {"": 0}
    return ARTICLE_MAP.get(article, 0)


def create_unit(unit_title: str, job: Job) -> Unit:
    """
    Create a new unit - even if one already exists with the same title.
    """
    unit = Unit.objects.create(title=unit_title)
    unit.jobs.add(job)
    return unit


def create_word(word_text: str, singular_article: int) -> Word:
    """
    Creates a new word object.
    """
    return Word.objects.create(word=word_text, singular_article=singular_article)


def update_or_add_example_sentence(word_obj: Word, word_defaults: dict) -> None:
    """
    Adds or edits example sentence to word object.
    """
    if word_obj.example_sentence != word_defaults["example_sentence"]:
        word_obj.example_sentence = word_defaults["example_sentence"]
        word_obj.save(update_fields=["example_sentence"])


def parse_row(raw_row: dict, row_number: int) -> ParsedRow | RowResult:
    """
    Parses a single row and returns either a ParsedRow or a RowResult (error).
    """
    try:
        mapped = {
            COLUMN_MAPPING[key.strip()]: (
                value.strip() if isinstance(value, str) else value
            )
            for key, value in raw_row.items()
            if key and COLUMN_MAPPING.get(key.strip())
        }

        if not mapped:
            raise InvalidRowError(
                _("Row %(n)s: No recognised columns – row will be skipped.")
                % {"n": row_number}
            )

        unknown_keys = {
            k.strip() for k in raw_row.keys() if k and not COLUMN_MAPPING.get(k.strip())
        }
        if unknown_keys:
            logger.info(
                "Row %s contains unexpected columns: %s",
                row_number,
                ", ".join(sorted(unknown_keys)),
            )

        unit = mapped.get("unit", "")
        if not unit:
            return RowResult(
                error=_("Row %(n)s: Unit column is empty, row will be skipped.")
                % {"n": row_number}
            )

        word = mapped.get("word", "")
        if not word:
            return RowResult(
                error=_("Row %(n)s: Vocabulary column is empty, row will be skipped.")
                % {"n": row_number}
            )

        article = mapped.get("article", "").lower()
        example = mapped.get("example", "")

        return ParsedRow(unit=unit, word=word, article=article, example=example)

    except (AttributeError, TypeError) as exc:
        logger.warning("Row %s – malformed column data: %s", row_number, exc)
        return RowResult(
            error=_("Row %(n)s: Malformed column data – %(e)s")
            % {"n": row_number, "e": exc}
        )
    except InvalidRowError as exc:
        logger.info("Row %s skipped: %s", row_number, exc)
        return RowResult(error=str(exc))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error while parsing row %s", row_number)
        return RowResult(
            error=_("Row %(n)s: Unexpected parsing error – %(e)s")
            % {"n": row_number, "e": exc}
        )


def process_row(
    parsed: ParsedRow,
    job: Job,
    created_units: Dict[str, Unit],
) -> RowResult:
    """
    Processes a single parsed row.

    If unit is not yet in ``created_units`` cache, a new unit gets created, even if there is already one in the system with the same name.
    If there is a unit in the cache, use that one
    Update example sentence
    Add word to newly created unit
    """
    created = 0
    updated = 0

    unit = created_units.get(parsed.unit)
    if unit is None:
        unit = create_unit(parsed.unit, job)
        created_units[parsed.unit] = unit
        created += 1
    else:
        if not unit.jobs.filter(pk=job.pk).exists():
            unit.jobs.add(job)

    article_int = map_article_to_int(parsed.article)
    word = create_word(parsed.word, article_int)
    created += 1

    update_or_add_example_sentence(word, {"example_sentence": parsed.example})

    unit.words.add(word)

    return RowResult(created=created, updated=updated)


def import_words_from_csv(dataset: Dataset, job: Job) -> Tuple[int, int, list[str]]:
    """
    Imports the entire csv dataset to a job.
    Returns a tuple of created_count, updated_count, error_messages

    Important: During the import there is a local cache ``created_units`` because of the following scenario:
    In the CSV file there are ten words for the unit "tools"
    There is already a unit called "tools" in the system
    What we want to happen is: a second unit "tools" is created, distinct from the one that already exists. All words
    in the CSV file gets imported into that second instance of "tools".
    """
    total_created = 0
    total_updated = 0
    error_messages: list[str] = []

    created_units: Dict[str, Unit] = {}

    for row_number, raw_row in enumerate(dataset.dict, start=1):
        parsed_or_error = parse_row(raw_row, row_number)

        if isinstance(parsed_or_error, RowResult):
            if parsed_or_error.error:
                error_messages.append(parsed_or_error.error)
            continue

        result = process_row(parsed_or_error, job, created_units)

        if result.error:
            error_messages.append(
                _("Row %(n)s: %(msg)s") % {"n": row_number, "msg": result.error}
            )
            continue

        total_created += result.created
        total_updated += result.updated

    return total_created, total_updated, error_messages
