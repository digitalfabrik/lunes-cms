import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, TYPE_CHECKING

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from tablib import Dataset

from ..models import (
    Job,
    PluralArticle,
    SingularArticle,
    Unit,
    UnitWordRelation,
    Word,
    WordType,
)

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
        # pronunciation
        "Pronunciation": "pronunciation",
        "Aussprache": "pronunciation",
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

#: The row the column headers occupy. The dataset's rows start below it, and
#: error messages count from the file so they name the row the editor sees.
HEADER_ROW = 1


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
class ParsedRow:  # pylint: disable=too-many-instance-attributes
    """
    Cleaned data for a single row: one attribute per recognised CSV column.
    """

    unit: str
    word: str
    article: str
    plural: str = ""
    plural_article: str = ""
    pronunciation: str = ""
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

    word_created: bool = False
    error: Optional[str] = None
    word_id: Optional[int] = None


@dataclass
class ImportSummary:
    """
    Outcome of importing one CSV file: how much content it added, which
    units it extended rather than created, and the rows it had to skip.
    """

    words_created: int = 0
    units_created: int = 0
    units_reused: int = 0
    errors: list[str] = field(default_factory=list)
    imported_word_ids: list[int] = field(default_factory=list)


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


@dataclass(frozen=True)
class WordAttributes:
    """The (already converted/validated) word fields a CSV row contributes."""

    singular_article: int
    plural_article: int | None
    plural: str = ""
    pronunciation: str = ""
    word_type: str = ""
    example_sentence: str = ""


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
        pronunciation=attributes.pronunciation,
        word_type=attributes.word_type,
        example_sentence=attributes.example_sentence,
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
        pronunciation = mapped.get("pronunciation", "")
        example = mapped.get("example", "")
        word_type = mapped.get("word_type", "")

        return ParsedRow(
            unit=unit,
            word=word,
            article=article,
            plural=plural,
            plural_article=plural_article,
            pronunciation=pronunciation,
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


class UnitResolver:
    """
    Maps the unit titles of an import onto unit objects: a title that the job
    already has a unit for extends that unit, any other title gets a new one.
    Keeps track of which titles went which way so the import can report both.
    """

    def __init__(self, job: Job, creator_fields: dict) -> None:
        self.job = job
        self.creator_fields = creator_fields
        self.units_by_title: Dict[str, Unit] = {
            unit.title: unit for unit in job.units.order_by("-pk")
        }
        self.created_titles: set[str] = set()
        self.reused_titles: set[str] = set()

    def resolve(self, unit_title: str) -> Unit:
        """
        Returns the unit the words of this title belong in, creating it if
        the job has none.
        """
        unit = self.units_by_title.get(unit_title)
        if unit is None:
            unit = Unit.objects.create(title=unit_title, **self.creator_fields)
            unit.jobs.add(self.job)
            self.units_by_title[unit_title] = unit
            self.created_titles.add(unit_title)
        elif unit_title not in self.created_titles:
            self.reused_titles.add(unit_title)
        return unit


def process_row(
    parsed: ParsedRow,
    units: UnitResolver,
    creator_fields: dict,
) -> RowResult:
    """
    Processes a single parsed row.

    The "unit" column may name more than one unit (see
    ``_split_unit_titles``); each one is resolved and linked to the word
    individually.
    """
    row_units = [units.resolve(title) for title in _split_unit_titles(parsed.unit)]

    attributes = WordAttributes(
        singular_article=map_article_to_int(parsed.article),
        plural_article=map_plural_article_to_int(parsed.plural_article),
        plural=parsed.plural,
        pronunciation=parsed.pronunciation,
        word_type=map_word_type(parsed.word_type),
        example_sentence=parsed.example,
    )
    word = create_word(parsed.word, attributes, creator_fields)

    # Bypasses ``unit.words.add``, which would first query for links that a
    # word created a line ago cannot have.
    UnitWordRelation.objects.bulk_create(
        UnitWordRelation(unit=unit, word=word) for unit in dict.fromkeys(row_units)
    )

    return RowResult(word_created=True, word_id=word.pk)


def import_words_from_csv(dataset: Dataset, job: Job, user: User) -> ImportSummary:
    """
    Imports the csv dataset into the job. A row that cannot be imported is
    collected in the summary's errors rather than aborting the rest.
    """
    summary = ImportSummary()
    creator_fields = _creator_fields_for_user(user)
    units = UnitResolver(job, creator_fields)

    for row_number, raw_row in enumerate(dataset.dict, start=HEADER_ROW + 1):
        parsed_or_error = parse_row(raw_row, row_number)

        if isinstance(parsed_or_error, RowResult):
            if parsed_or_error.error:
                summary.errors.append(parsed_or_error.error)
            continue

        result = process_row(parsed_or_error, units, creator_fields)

        if result.error:
            summary.errors.append(
                _("Row %(n)s: %(msg)s") % {"n": row_number, "msg": result.error}
            )
            continue

        if result.word_created:
            summary.words_created += 1
        if result.word_id is not None:
            summary.imported_word_ids.append(result.word_id)

    summary.units_created = len(units.created_titles)
    summary.units_reused = len(units.reused_titles)
    return summary
