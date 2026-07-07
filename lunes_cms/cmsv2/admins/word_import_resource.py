import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from django.utils.translation import gettext_lazy as _
from tablib import Dataset

from ..models import Job, PluralArticle, SingularArticle, Unit, Word

logger = logging.getLogger(__name__)


def _build_column_mapping() -> dict[str, str]:
    """
    Maps CSV column headers (from the exporter or legacy templates) to internal
    field names. Both German and English export headers are listed explicitly
    since the exported CSV uses the language of the admin interface at export
    time.
    """
    return {
        # unit
        "Units": "unit",
        "Einheit": "unit",
        # word
        "Word": "word",
        "Vokabel": "word",
        # singular article
        "Singular Article": "article",
        "Singularartikel": "article",
        # plural word
        "Plural": "plural",
        # plural article
        "Plural Article": "plural_article",
        "Pluralartikel": "plural_article",
        # example sentence
        "Example sentence": "example",
        "Beispielsatz": "example",
        # For legacy imports
        "Artikel": "article",
        "Fachbegriff": "word",
        "Begriff": "word",
        "Sinneinheit": "unit",
        "Sinneseinheit": "unit",
    }


@dataclass(frozen=True)
class ParsedRow:
    """
    Cleaned data for a single row
    """

    unit: str
    word: str
    article: str
    plural: str = ""
    plural_article: str = ""
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

    unit_created: bool = False
    word_created: bool = False
    error: Optional[str] = None
    word_id: Optional[int] = None


def map_article_to_int(article: str) -> int:
    """
    Converts article string to article int in DB.
    """
    ARTICLE_MAP: dict[str, int] = {
        label.lower(): value for value, label in SingularArticle.choices
    } | {"": 0}
    return ARTICLE_MAP.get(article, 0)


def map_plural_article_to_int(plural_article: str) -> int | None:
    """
    Converts plural article string to its int in DB. Returns None for empty or
    unknown values (the field is nullable).
    """
    ARTICLE_MAP: dict[str, int] = {
        label.lower(): value for value, label in PluralArticle.choices
    } | {
        label.lower().replace(" (plural)", ""): value
        for value, label in PluralArticle.choices
    }
    normalized = plural_article.lower().strip()
    return ARTICLE_MAP.get(normalized)


def create_unit(unit_title: str, job: Job) -> Unit:
    """
    Create a new unit - even if one already exists with the same title.
    """
    unit = Unit.objects.create(title=unit_title)
    unit.jobs.add(job)
    return unit


def create_word(
    word_text: str, singular_article: int, plural_article: int | None, plural: str = ""
) -> Word:
    """
    Creates a new word object.
    """
    return Word.objects.create(
        word=word_text,
        singular_article=singular_article,
        plural_article=plural_article,
        plural=plural,
    )


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
        column_mapping = {k.lower(): v for k, v in _build_column_mapping().items()}
        mapped = {
            column_mapping[key.strip().lower()]: (
                value.strip() if isinstance(value, str) else value
            )
            for key, value in raw_row.items()
            if key and column_mapping.get(key.strip().lower())
        }

        if not mapped:
            raise InvalidRowError(
                _("Row %(n)s: No recognised columns – row will be skipped.")
                % {"n": row_number}
            )

        unknown_keys = {
            k.strip() for k in raw_row.keys() if k and not column_mapping.get(k.strip())
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
        plural = mapped.get("plural", "")
        plural_article = mapped.get("plural_article", "")
        example = mapped.get("example", "")

        return ParsedRow(
            unit=unit,
            word=word,
            article=article,
            plural=plural,
            plural_article=plural_article,
            example=example,
        )

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
    unit_created = False

    unit = created_units.get(parsed.unit)
    if unit is None:
        unit = create_unit(parsed.unit, job)
        created_units[parsed.unit] = unit
        unit_created = True
    else:
        if not unit.jobs.filter(pk=job.pk).exists():
            unit.jobs.add(job)

    article_int = map_article_to_int(parsed.article)
    plural_article_int = map_plural_article_to_int(parsed.plural_article)
    word = create_word(parsed.word, article_int, plural_article_int, parsed.plural)

    update_or_add_example_sentence(word, {"example_sentence": parsed.example})

    unit.words.add(word)

    return RowResult(unit_created=unit_created, word_created=True, word_id=word.pk)


def import_words_from_csv(
    dataset: Dataset, job: Job
) -> Tuple[int, int, list[str], list[int]]:
    """
    Imports the entire csv dataset to a job.
    Returns a tuple of words_created_count, units_created_count, error_messages,
    imported_word_ids

    Important: During the import there is a local cache ``created_units`` because of the following scenario:
    In the CSV file there are ten words for the unit "tools"
    There is already a unit called "tools" in the system
    What we want to happen is: a second unit "tools" is created, distinct from the one that already exists. All words
    in the CSV file gets imported into that second instance of "tools".
    """
    total_words_created = 0
    total_units_created = 0
    error_messages: list[str] = []
    imported_word_ids: list[int] = []

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

        if result.word_created:
            total_words_created += 1
        if result.unit_created:
            total_units_created += 1
        if result.word_id is not None:
            imported_word_ids.append(result.word_id)

    return total_words_created, total_units_created, error_messages, imported_word_ids
