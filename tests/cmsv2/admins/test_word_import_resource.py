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
    parse_row,
    ParsedRow,
    RowResult,
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
    assert mapping["Singular Article"] == "article"
    assert mapping["Plural"] == "plural"
    assert mapping["Plural Article"] == "plural_article"
    assert mapping["Example sentence"] == "example"


def test_legacy_column_names_are_mapped() -> None:
    """Legacy column names from older import templates are still recognised."""
    mapping = _build_column_mapping()
    assert mapping["Sinneinheit"] == "unit"
    assert mapping["Sinneseinheit"] == "unit"
    assert mapping["Fachbegriff"] == "word"
    assert mapping["Begriff"] == "word"
    assert mapping["Artikel"] == "article"


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
    """Return queryset of words imported into the given job."""
    return Word.objects.filter(units__jobs=job)


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
    """Extra columns from the export (Word type, Has audio?, Creation date) don't cause errors."""
    ds = _make_dataset(
        [
            "Units",
            "Word",
            "Singular Article",
            "Word type",
            "Has audio?",
            "Creation date",
        ],
        [["Werkzeug", "Hammer", "der", "noun", "No", "01.01.2026 10:00"]],
    )
    _, _, errors, _ = import_words_from_csv(ds, job, user)
    assert errors == []
    assert _job_words(job).count() == 1


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
