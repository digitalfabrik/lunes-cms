import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from tablib import Dataset

from ..models import Job, PluralArticle, SingularArticle, Unit, Word, WordType

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise

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
        # word type
        "Word type": "word_type",
        "Wortart": "word_type",
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


def _lowered_column_mapping() -> dict[str, str]:
    return {key.lower(): value for key, value in _build_column_mapping().items()}


#: Internal fields without which a row can't be imported at all — every
#: other recognised column (article, plural, example sentence, word type)
#: has a usable default and doesn't need to be filled in.
REQUIRED_FIELDS = ("unit", "word")


def validate_header_structure(
    headers: Optional[list[str]],
) -> "Optional[_StrOrPromise]":
    """
    Checks that the dataset's header row contains the structurally required
    columns (unit and word). Returns a translated error message if the file
    doesn't look like an import file at all, or ``None`` if the required
    columns were found. The expected columns themselves are already named in
    ``ImportCSVForm``'s ``csv_file`` help text, so the message doesn't repeat
    them.
    """
    column_mapping = _lowered_column_mapping()
    mapped_fields = {
        column_mapping[header.strip().lower()]
        for header in headers or []
        if header and column_mapping.get(header.strip().lower())
    }
    if set(REQUIRED_FIELDS) <= mapped_fields:
        return None
    return _("The file is not in the correct format.")


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
    word_type: str = ""


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

    units_created: int = 0
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


def map_word_type(word_type: str) -> str:
    """
    Validates a word type string (as produced by the exporter) against the
    known ``WordType`` values, case-insensitively. Returns "" (the model
    default) for empty or unrecognised values, rather than failing the row.
    """
    WORD_TYPE_MAP: dict[str, str] = {value.lower(): value for value in WordType.values}
    return WORD_TYPE_MAP.get(word_type.lower().strip(), "")


def create_unit(unit_title: str, job: Job, creator_fields: dict) -> Unit:
    """
    Create a new unit - even if one already exists with the same title.
    """
    unit = Unit.objects.create(title=unit_title, **creator_fields)
    unit.jobs.add(job)
    return unit


@dataclass(frozen=True)
class WordAttributes:
    """The (already converted/validated) word fields a CSV row contributes."""

    singular_article: int
    plural_article: int | None
    plural: str = ""
    word_type: str = ""


def create_word(
    word_text: str, attributes: WordAttributes, creator_fields: dict
) -> Word:
    """
    Creates a new word object.
    """
    return Word.objects.create(
        word=word_text,
        singular_article=attributes.singular_article,
        plural_article=attributes.plural_article,
        plural=attributes.plural,
        word_type=attributes.word_type,
        **creator_fields,
    )


def _creator_fields_for_user(user: User) -> dict:
    """
    Builds the created_by/created_by_user/creator_is_admin values a CSV
    import should stamp on the units and words it creates, mirroring how
    BaseAdmin.save_model attributes objects created through the admin forms.
    """
    if user.groups.exists():
        group = user.groups.first()
    elif not user.is_superuser:
        raise IndexError("No group assigned. Please add the user to a group")
    else:
        group = None
    return {
        "created_by": group,
        "created_by_user": user,
        "creator_is_admin": user.is_superuser,
    }


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
        column_mapping = _lowered_column_mapping()
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
        word_type = mapped.get("word_type", "")

        return ParsedRow(
            unit=unit,
            word=word,
            article=article,
            plural=plural,
            plural_article=plural_article,
            example=example,
            word_type=word_type,
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


def _split_unit_titles(unit_column: str) -> list[str]:
    """
    Splits the "unit" column into individual unit titles. The exporter joins
    a word's units with " | " when it belongs to several units of the same
    job (see ``WordExportResource.dehydrate_units``) — on re-import that
    joined string must resolve back to each of those units individually,
    not to one new unit literally named e.g. "Werkzeuge | Baustelle".
    """
    titles = (part.strip() for part in unit_column.split("|"))
    return [title for title in titles if title]


def _resolve_unit(
    unit_title: str,
    job: Job,
    created_units: Dict[str, Unit],
    creator_fields: dict,
) -> Tuple[Unit, bool]:
    """
    Looks up ``unit_title`` in the ``created_units`` cache, creating it (even
    if a unit with the same title already exists elsewhere) if this is the
    first time this import encounters it. Returns the unit and whether it
    was newly created.
    """
    unit = created_units.get(unit_title)
    if unit is None:
        unit = create_unit(unit_title, job, creator_fields)
        created_units[unit_title] = unit
        return unit, True

    if not unit.jobs.filter(pk=job.pk).exists():
        unit.jobs.add(job)
    return unit, False


def process_row(
    parsed: ParsedRow,
    job: Job,
    created_units: Dict[str, Unit],
    creator_fields: dict,
) -> RowResult:
    """
    Processes a single parsed row.

    The "unit" column may name more than one unit (see
    ``_split_unit_titles``); each one is resolved/created and linked to the
    word individually. Update example sentence. Add word to newly created
    unit(s).
    """
    units_created = 0
    units = []
    for unit_title in _split_unit_titles(parsed.unit):
        unit, created = _resolve_unit(unit_title, job, created_units, creator_fields)
        units.append(unit)
        if created:
            units_created += 1

    attributes = WordAttributes(
        singular_article=map_article_to_int(parsed.article),
        plural_article=map_plural_article_to_int(parsed.plural_article),
        plural=parsed.plural,
        word_type=map_word_type(parsed.word_type),
    )
    word = create_word(parsed.word, attributes, creator_fields)

    update_or_add_example_sentence(word, {"example_sentence": parsed.example})

    for unit in units:
        unit.words.add(word)

    return RowResult(units_created=units_created, word_created=True, word_id=word.pk)


def import_words_from_csv(
    dataset: Dataset, job: Job, user: User
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

    creator_fields = _creator_fields_for_user(user)
    created_units: Dict[str, Unit] = {}

    for row_number, raw_row in enumerate(dataset.dict, start=1):
        parsed_or_error = parse_row(raw_row, row_number)

        if isinstance(parsed_or_error, RowResult):
            if parsed_or_error.error:
                error_messages.append(parsed_or_error.error)
            continue

        result = process_row(parsed_or_error, job, created_units, creator_fields)

        if result.error:
            error_messages.append(
                _("Row %(n)s: %(msg)s") % {"n": row_number, "msg": result.error}
            )
            continue

        if result.word_created:
            total_words_created += 1
        total_units_created += result.units_created
        if result.word_id is not None:
            imported_word_ids.append(result.word_id)

    return total_words_created, total_units_created, error_messages, imported_word_ids
