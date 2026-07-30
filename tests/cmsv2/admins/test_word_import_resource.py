"""
Tests for the CSV word import resource (column mapping, row parsing, full import).
Covers the re-import workflow described in issue #775.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.db.models import QuerySet
from tablib import Dataset

from lunes_cms.cmsv2.admins.word_import_resource import (
    _build_column_mapping,
    import_words_from_csv,
    map_plural_article_to_int,
    map_word_type,
    parse_row,
    ParsedRow,
    RowResult,
    validate_header_structure,
)
from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.job import Job

# ---------------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------------


def test_german_export_columns_are_mapped() -> None:
    """German column names produced by the exporter are recognised."""
    mapping = _build_column_mapping()
    assert mapping["Einheit"] == "unit"
    assert mapping["Vokabel"] == "word"
    assert mapping["Singularartikel"] == "article"
    assert mapping["Plural"] == "plural"
    assert mapping["Pluralartikel"] == "plural_article"
    assert mapping["Beispielsatz"] == "example"


def test_english_export_columns_are_mapped() -> None:
    """English column names produced by the exporter are recognised."""
    mapping = _build_column_mapping()
    assert mapping["Units"] == "unit"
    assert mapping["Word"] == "word"
    assert mapping["Word type"] == "word_type"
    assert mapping["Singular Article"] == "article"
    assert mapping["Plural"] == "plural"
    assert mapping["Plural Article"] == "plural_article"
    assert mapping["Example sentence"] == "example"


def test_german_word_type_column_is_mapped() -> None:
    """The German "Wortart" header produced by the exporter is recognised."""
    assert _build_column_mapping()["Wortart"] == "word_type"


def test_legacy_column_names_are_mapped() -> None:
    """Legacy column names from older import templates are still recognised."""
    mapping = _build_column_mapping()
    assert mapping["Sinneinheit"] == "unit"
    assert mapping["Sinneseinheit"] == "unit"
    assert mapping["Fachbegriff"] == "word"
    assert mapping["Begriff"] == "word"
    assert mapping["Artikel"] == "article"


# ---------------------------------------------------------------------------
# validate_header_structure
# ---------------------------------------------------------------------------


def test_validate_header_structure_accepts_german_headers() -> None:
    assert validate_header_structure(["Einheit", "Vokabel", "Artikel"]) is None


def test_validate_header_structure_accepts_english_headers() -> None:
    assert validate_header_structure(["Units", "Word", "Singular Article"]) is None


def test_validate_header_structure_does_not_require_optional_columns() -> None:
    """Article, plural, plural article, example sentence and word type all
    have usable defaults — only unit and word are structurally required."""
    assert validate_header_structure(["Einheit", "Vokabel"]) is None


def test_validate_header_structure_rejects_missing_unit_column() -> None:
    assert validate_header_structure(["Vokabel", "Artikel"]) is not None


def test_validate_header_structure_rejects_missing_word_column() -> None:
    error = validate_header_structure(["Einheit", "Artikel"])
    assert error is not None


def test_validate_header_structure_rejects_unrecognised_headers() -> None:
    """A file whose header row matches none of the known columns at all
    (e.g. a non-CSV text file tablib parsed as one giant header) is rejected."""
    error = validate_header_structure(["this is not a csv file at all"])
    assert error is not None


def test_validate_header_structure_rejects_no_headers_at_all() -> None:
    """A completely empty file (tablib reports ``headers=None``) is rejected."""
    assert validate_header_structure(None) is not None


# ---------------------------------------------------------------------------
# map_plural_article_to_int
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("die (Plural)", 1),
        ("DIE (PLURAL)", 1),
        ("die", 1),
        ("DIE", 1),
        ("keiner", 0),
        ("", None),
        ("-", None),
        ("unknown", None),
    ],
)
def test_map_plural_article_to_int(value: str, expected: int | None) -> None:
    assert map_plural_article_to_int(value) == expected


# ---------------------------------------------------------------------------
# map_word_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Nomen", "Nomen"),
        ("NOMEN", "Nomen"),
        (" verb ", "Verb"),
        ("", ""),
        ("unknown", ""),
        ("noun", ""),  # English label isn't a stored value, unlike Nomen
    ],
)
def test_map_word_type(value: str, expected: str) -> None:
    assert map_word_type(value) == expected


# ---------------------------------------------------------------------------
# parse_row
# ---------------------------------------------------------------------------


def _make_row(**overrides: str) -> dict[str, str]:
    row = {"Einheit": "Werkzeug", "Vokabel": "Hammer", "Artikel": "der"}
    row.update(overrides)
    return row


def test_parse_row_returns_parsed_row() -> None:
    result = parse_row(_make_row(), 1)
    assert isinstance(result, ParsedRow)
    assert result.unit == "Werkzeug"
    assert result.word == "Hammer"
    assert result.article == "der"


def test_parse_row_parses_plural_article() -> None:
    result = parse_row(_make_row(**{"Pluralartikel": "die (Plural)"}), 1)
    assert isinstance(result, ParsedRow)
    assert result.plural_article == "die (Plural)"


def test_parse_row_parses_example_sentence() -> None:
    result = parse_row(_make_row(Beispielsatz="Der Hammer ist schwer."), 1)
    assert isinstance(result, ParsedRow)
    assert result.example == "Der Hammer ist schwer."


def test_parse_row_parses_word_type() -> None:
    result = parse_row(_make_row(Wortart="Nomen"), 1)
    assert isinstance(result, ParsedRow)
    assert result.word_type == "Nomen"


def test_parse_row_english_column_names() -> None:
    row = {
        "Units": "Werkzeug",
        "Word": "Hammer",
        "Singular Article": "der",
        "Plural Article": "die (Plural)",
        "Example sentence": "Der Hammer ist schwer.",
    }
    result = parse_row(row, 1)
    assert isinstance(result, ParsedRow)
    assert result.unit == "Werkzeug"
    assert result.word == "Hammer"
    assert result.article == "der"
    assert result.plural_article == "die (Plural)"
    assert result.example == "Der Hammer ist schwer."


def test_parse_row_missing_unit_returns_error() -> None:
    result = parse_row(_make_row(Einheit=""), 1)
    assert isinstance(result, RowResult)
    assert result.error is not None


def test_parse_row_missing_word_returns_error() -> None:
    result = parse_row(_make_row(Vokabel=""), 1)
    assert isinstance(result, RowResult)
    assert result.error is not None


def test_parse_row_no_recognised_columns_returns_error() -> None:
    result = parse_row({"Unknown": "value"}, 1)
    assert isinstance(result, RowResult)
    assert result.error is not None


def test_parse_row_strips_whitespace_from_column_names() -> None:
    row = {" Einheit ": "Werkzeug", " Vokabel ": "Hammer", " Artikel ": "der"}
    result = parse_row(row, 1)
    assert isinstance(result, ParsedRow)


# ---------------------------------------------------------------------------
# import_words_from_csv — integration
# ---------------------------------------------------------------------------


def _make_dataset(headers: list[str], rows: list[list[Any]]) -> Dataset:
    ds = Dataset(headers=headers)
    for row in rows:
        ds.append(row)
    return ds


@pytest.fixture
def job(db: None) -> Job:
    return Job.objects.create(name="Test Job")


@pytest.fixture
def user(db: None) -> User:
    return get_user_model().objects.create_superuser(
        username="importer", email="importer@example.com", password="password"
    )


def _job_words(job: Job) -> QuerySet[Word]:
    """
    Return queryset of words imported into the given job. ``distinct()`` is
    required because a word linked to more than one unit of the same job
    would otherwise join into more than one row.
    """
    return Word.objects.filter(units__jobs=job).distinct()


@pytest.mark.django_db
def test_import_with_german_headers(job: Job, user: User) -> None:
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel"],
        [["Werkzeug", "Hammer", "der"], ["Werkzeug", "Säge", "die"]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    assert _job_words(job).count() == 2


@pytest.mark.django_db
def test_reimport_with_english_headers(job: Job, user: User) -> None:
    """Re-import of a CSV exported with English admin locale works (issue #775)."""
    ds = _make_dataset(
        ["Units", "Word", "Singular Article", "Plural Article", "Example sentence"],
        [["Werkzeug", "Hammer", "der", "die (Plural)", "Der Hammer ist schwer."]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    word = _job_words(job).get(word="Hammer")
    assert word.plural_article == 1
    assert word.example_sentence == "Der Hammer ist schwer."


@pytest.mark.django_db
def test_imported_word_with_example_sentence_is_not_checked(
    job: Job, user: User
) -> None:
    """Issue #917: a word imported with an example sentence must not appear
    pre-confirmed — its example_sentence_check_status must persist as
    NOT_CHECKED, matching the default a manually created word gets."""
    ds = _make_dataset(
        ["Units", "Word", "Singular Article", "Example sentence"],
        [["Werkzeug", "Hammer", "der", "Der Hammer ist schwer."]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    word = _job_words(job).get(word="Hammer")
    assert word.example_sentence == "Der Hammer ist schwer."
    assert word.example_sentence_check_status == "NOT_CHECKED"
    assert word.audio_check_status == "NOT_CHECKED"
    assert word.image_check_status == "NOT_CHECKED"


@pytest.mark.django_db
def test_reimport_with_german_headers(job: Job, user: User) -> None:
    """Re-import of a CSV exported with German admin locale works (issue #775)."""
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Singularartikel", "Pluralartikel", "Beispielsatz"],
        [["Werkzeug", "Hammer", "der", "die (Plural)", "Der Hammer ist schwer."]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    assert _job_words(job).get(word="Hammer").plural_article == 1


@pytest.mark.django_db
def test_import_plural_word(job: Job, user: User) -> None:
    """The Plural column is imported and stored on the word."""
    ds = _make_dataset(
        ["Units", "Word", "Singular Article", "Plural", "Plural Article"],
        [["Werkzeug", "Hammer", "der", "Hämmer", "die"]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    word = _job_words(job).get(word="Hammer")
    assert word.plural == "Hämmer"
    assert word.plural_article == 1


@pytest.mark.django_db
def test_plural_article_short_form_stored(job: Job, user: User) -> None:
    """'die' (short form exported by the exporter) is stored as plural article 1."""
    ds = _make_dataset(
        ["Units", "Word", "Singular Article", "Plural Article"],
        [["Werkzeug", "Hammer", "der", "die"]],
    )
    import_words_from_csv(ds, job, user)
    assert _job_words(job).get(word="Hammer").plural_article == 1


@pytest.mark.django_db
def test_plural_article_dash_stored_as_none(job: Job, user: User) -> None:
    """'-' in the plural article column (exporter default) is stored as None."""
    ds = _make_dataset(
        ["Units", "Word", "Singular Article", "Plural Article"],
        [["Werkzeug", "Hammer", "der", "-"]],
    )
    import_words_from_csv(ds, job, user)
    assert _job_words(job).get(word="Hammer").plural_article is None


@pytest.mark.django_db
def test_extra_export_columns_are_ignored(job: Job, user: User) -> None:
    """Has audio? and Creation date are export-only metadata columns with no
    matching field to import into — they must not cause errors."""
    ds = _make_dataset(
        ["Units", "Word", "Singular Article", "Has audio?", "Creation date"],
        [["Werkzeug", "Hammer", "der", "No", "01.01.2026 10:00"]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    assert _job_words(job).count() == 1


@pytest.mark.django_db
def test_word_type_column_is_imported(job: Job, user: User) -> None:
    """Word type — previously silently dropped on re-import — is now stored."""
    ds = _make_dataset(
        ["Units", "Word", "Singular Article", "Word type"],
        [["Werkzeug", "Hammer", "der", "Nomen"]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    assert _job_words(job).get(word="Hammer").word_type == "Nomen"


@pytest.mark.django_db
def test_unrecognised_word_type_defaults_to_empty(job: Job, user: User) -> None:
    """An unrecognised word type value doesn't fail the row, just falls back
    to the model default instead of being stored verbatim."""
    ds = _make_dataset(
        ["Units", "Word", "Singular Article", "Word type"],
        [["Werkzeug", "Hammer", "der", "not-a-real-type"]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    assert _job_words(job).get(word="Hammer").word_type == ""


@pytest.mark.django_db
def test_empty_rows_produce_errors(job: Job, user: User) -> None:
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel"],
        [["", "Hammer", "der"], ["Werkzeug", "", "der"]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert len(errors) == 2
    assert _job_words(job).count() == 0


@pytest.mark.django_db
def test_imported_words_and_units_are_attributed_to_the_importing_user(
    job: Job, user: User
) -> None:
    """Units and words created by a CSV import record who created them, not just their group."""
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel"],
        [["Werkzeug", "Hammer", "der"]],
    )
    import_words_from_csv(ds, job, user)

    word = _job_words(job).get(word="Hammer")
    unit = word.units.get()
    assert word.created_by_user == user
    assert word.creator_is_admin is True
    assert unit.created_by_user == user
    assert unit.creator_is_admin is True


@pytest.mark.django_db
def test_imported_words_are_attributed_to_the_importing_users_group(job: Job) -> None:
    """Units and words created by a CSV import inherit the importing user's group."""
    group = Group.objects.create(name="Importers")
    non_admin_user = get_user_model().objects.create_user(
        username="non_admin_importer", password="password"
    )
    non_admin_user.groups.add(group)

    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel"],
        [["Werkzeug", "Hammer", "der"]],
    )
    import_words_from_csv(ds, job, non_admin_user)

    word = _job_words(job).get(word="Hammer")
    assert word.created_by == group
    assert word.creator_is_admin is False


@pytest.mark.django_db
def test_import_raises_if_user_has_no_group_and_is_not_superuser(
    job: Job,
) -> None:
    """A non-admin user without a group cannot own the imported content."""
    orphan_user = get_user_model().objects.create_user(
        username="orphan", password="password"
    )
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel"],
        [["Werkzeug", "Hammer", "der"]],
    )
    with pytest.raises(IndexError):
        import_words_from_csv(ds, job, orphan_user)


# ---------------------------------------------------------------------------
# pronunciation column
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("header", ["Aussprache", "Pronunciation"])
def test_parse_row_reads_the_pronunciation_column(header: str) -> None:
    row = {
        "Einheit": "Backwaren",
        "Vokabel": "Baiser",
        "Artikel": "das",
        header: "Bessee",
    }

    result = parse_row(row, 1)

    assert isinstance(result, ParsedRow)
    assert result.pronunciation == "Bessee"


def test_parse_row_defaults_pronunciation_to_empty() -> None:
    row = {"Einheit": "Werkzeug", "Vokabel": "Hammer", "Artikel": "der"}

    result = parse_row(row, 1)

    assert isinstance(result, ParsedRow)
    assert result.pronunciation == ""


@pytest.mark.django_db
def test_import_stores_pronunciation_on_the_word(job: Job, user: User) -> None:
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel", "Aussprache"],
        [["Backwaren", "Baiser", "das", "Bessee"], ["Werkzeug", "Hammer", "der", ""]],
    )

    _, _, errors, _ = import_words_from_csv(ds, job, user)

    assert errors == []
    assert _job_words(job).get(word="Baiser").pronunciation == "Bessee"
    assert _job_words(job).get(word="Hammer").pronunciation == ""


# ---------------------------------------------------------------------------
# Multi-unit words ("Units" column joined with " | ", see issue #738)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pipe_separated_units_are_split_and_both_linked(job: Job, user: User) -> None:
    """A word exported from two units of the same job (joined with " | " by
    ``WordExportResource.dehydrate_units``) must re-import into *both* of
    those units, not into one new unit literally named "A | B"."""
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel"],
        [["Werkzeuge | Baustelle", "Hammer", "der"]],
    )
    _, units_created, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    word = _job_words(job).get(word="Hammer")
    assert set(word.units.values_list("title", flat=True)) == {
        "Werkzeuge",
        "Baustelle",
    }
    assert units_created == 2


@pytest.mark.django_db
def test_pipe_separated_units_tolerate_missing_spaces(job: Job, user: User) -> None:
    """The split is lenient about whitespace around the "|" separator, not
    just the exact " | " the exporter happens to produce."""
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel"],
        [["Werkzeuge|Baustelle", "Hammer", "der"]],
    )
    import_words_from_csv(ds, job, user)
    word = _job_words(job).get(word="Hammer")
    assert set(word.units.values_list("title", flat=True)) == {
        "Werkzeuge",
        "Baustelle",
    }


@pytest.mark.django_db
def test_pipe_separated_units_reuse_the_row_cache(job: Job, user: User) -> None:
    """Two rows naming the same multi-unit combination reuse the same two
    units (via the ``created_units`` cache) instead of creating duplicates."""
    ds = _make_dataset(
        ["Einheit", "Vokabel", "Artikel"],
        [
            ["Werkzeuge | Baustelle", "Hammer", "der"],
            ["Werkzeuge | Baustelle", "Säge", "die"],
        ],
    )
    _, units_created, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    assert units_created == 2
    hammer = _job_words(job).get(word="Hammer")
    saege = _job_words(job).get(word="Säge")
    assert set(hammer.units.values_list("pk", flat=True)) == set(
        saege.units.values_list("pk", flat=True)
    )
