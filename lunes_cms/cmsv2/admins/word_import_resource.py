import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

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
    Clean dataset of a single parsed row
    """

    unit: str
    word: str
    article: str
    example: str = ""


class InvalidRowError(ValueError):
    """
    Raised when a CSV row does not contain any of the expected columns.
    """


@dataclass
class RowResult:
    """
    Return object of a single row
    """

    created: int = 0
    updated: int = 0
    error: Optional[str] = None


@dataclass
class AdjustmentLog:
    row_number: int
    original: Dict[str, Any]
    adjusted: Dict[str, Any]
    action: str


def import_words_from_csv(dataset: Dataset, job: Job) -> tuple[int, int, list[str]]:
    """
    Imports words from a tablib Dataset into the given job.

    Expected CSV columns: "Einheit", "Artikel" (der/die/das), "Vokabel", "Beispielsatz"

    Returns:
        A tuple of (created_count, updated_count, error_messages)
    """
    total_created = 0
    total_updated = 0
    errors: list[str] = []
    adjustments: list[AdjustmentLog] = []

    EXPECTED_COLUMNS = len(COLUMN_MAPPING)
    for row_number, raw_row in enumerate(dataset.dict, start=1):
        adjusted_row, changed, action = adjust_row_dimensions(
            raw_row, EXPECTED_COLUMNS, pad_value=""
        )
        if changed:
            adjustments.append(
                AdjustmentLog(
                    row_number=row_number,
                    original=raw_row,
                    adjusted=adjusted_row,
                    action=action,
                )
            )
        parsed_or_error = parse_row(adjusted_row, row_number)
        if isinstance(parsed_or_error, RowResult):
            errors.append(parsed_or_error.error)
            continue

        result = process_row(parsed_or_error, job)

        if result.error:
            errors.append(
                _("Row %(n)s: %(msg)s") % {"n": row_number, "msg": result.error}
            )
            continue

        total_created += result.created
        total_updated += result.updated

    return total_created, total_updated, error_messages


def map_article_to_int(article: str) -> int:
    """
    Convert article string into article int for DB
    """

    ARTICLE_MAP: dict[str, int] = {
        label.lower(): value for value, label in Static.singular_article_choices
    } | {"": 0}
    return ARTICLE_MAP.get(article, 0)


def create_unit(unit_title: str, job: Job) -> Unit:
    """
    Creates a new unit, even if one of the same name already exists. This is intended.
    Words with the same title are considered less harming than having a unit in your job that only partially fits your learning interest.
    """
    unit = Unit.objects.create(title=unit_title)
    unit.jobs.add(job)
    return unit


def create_word(word_text: str, article_int: int, example: str) -> tuple[Word, bool]:
    """
    Gets a word if it exists or creates it if it didn't yet exist. This way we avoid duplicates.
    Also returns a flag which case it was.
    """
    defaults = {"singular_article": article_int, "example_sentence": example}
    word, created = Word.objects.create(word=word_text, defaults=defaults)
    return word, created


def update_or_add_example_sentence(created_word, word_obj, word_defaults) -> None:
    """
    Method to either update or add an example sentence. We want to do it this way to avoid duplicates.
    """
    if (
        not created_word
        and word_obj.example_sentence != word_defaults["example_sentence"]
    ):
        word_obj.example_sentence = word_defaults["example_sentence"]
        word_obj.save(update_fields=["example_sentence"])


def adjust_row_dimensions(
    row: dict, expected_len: int, *, pad_value: str = ""
) -> tuple[dict, bool, str]:
    """
    Correct number of count

    Returns
    -------
    tuple
        (adjusted_row, changed, action)
        - adjusted_row: ggf. korrigiertes dict
        - changed:        True, wenn etwas geändert wurde
        - action:         "padded" | "truncated" | ""
    """
    keys = list(row.keys())
    values = list(row.values())

    if len(values) == expected_len:
        return row, False, ""

    if len(values) > expected_len:
        keys = keys[:expected_len]
        values = values[:expected_len]
        action = "truncated"

    adjusted_row = dict(zip(keys, values))
    return adjusted_row, True, action


def parse_row(raw_row: dict, row_number: int) -> ParsedRow | RowResult:
    """
    Parses a single CSV row and either returns a ParsedRow if everything is okay, or RowResult if there is an error.
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
        # we want to catch any unexpected error here to avoid breaking the whole import
        logger.exception("Unexpected error while parsing row %s", row_number)
        return RowResult(
            error=_("Row %(n)s: Unexpected parsing error – %(e)s")
            % {"n": row_number, "e": exc}
        )


def process_row(parsed: ParsedRow, job: Job) -> RowResult:
    """
    Makes all DB operations for one row.
    """
    created = 0
    updated = 0

    try:
        unit = create_unit(parsed.unit, job)

        article_int = map_article_to_int(parsed.article)

        word, is_new = create_word(parsed.word, article_int, parsed.example)

        update_or_add_example_sentence(
            is_new, word, {"example_sentence": parsed.example}
        )

        unit.words.add(word)

        if is_new:
            created += 1
        else:
            updated += 1
        return RowResult(created=created, updated=updated)

    except ValueError as exc:
        logger.exception("Unexpected error processing row with word=%s", parsed.word)
        return RowResult(error=_("Unexpected error - %(e)s") % {"e": exc})
