"""
Tests for scoping the "Units" export column to the exported job (issue #738).

``WordExportResource`` used to fall back to a word's *entire* global unit
list whenever it wasn't scoped to a profession — and the only real caller
(``JobAdmin.export_to_csv``) never passed a profession in the first place
(it called ``for_profession.get_nested_units()``, a method that doesn't
exist on ``Job`` and was therefore dead code). The practical effect: a CSV
exported for one job could list unit names belonging to a completely
unrelated job in its "Units" column.
"""

from __future__ import annotations

import pytest

from lunes_cms.cmsv2.admins.word_export_resource import WordExportResource
from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation


def _link(unit: Unit, word: Word) -> UnitWordRelation:
    return UnitWordRelation.objects.create(unit=unit, word=word)


@pytest.mark.django_db()
def test_dehydrate_units_only_lists_units_of_the_exported_job() -> None:
    """A word taught in units of two unrelated jobs must only show the
    exported job's own unit — not the other job's."""
    job_a = Job.objects.create(name="Bäcker/-in")
    job_b = Job.objects.create(name="Kfz-Mechatroniker/-in")
    unit_a = Unit.objects.create(title="Backofen")
    unit_a.jobs.add(job_a)
    unit_b = Unit.objects.create(title="Bremsen")
    unit_b.jobs.add(job_b)
    word = Word.objects.create(word="Schraubenzieher", singular_article=1)
    _link(unit_a, word)
    _link(unit_b, word)

    resource = WordExportResource(for_profession=job_a)

    assert resource.dehydrate_units(word) == "Backofen"


@pytest.mark.django_db()
def test_dehydrate_units_still_lists_multiple_units_of_the_same_job() -> None:
    """A word in two units of the *same* exported job still shows both —
    only cross-job leakage is what's being fixed here, not this (intentional,
    see issue #531) same-job multi-unit case."""
    job = Job.objects.create(name="Bäcker/-in")
    unit_1 = Unit.objects.create(title="Backofen")
    unit_1.jobs.add(job)
    unit_2 = Unit.objects.create(title="Küchengeräte")
    unit_2.jobs.add(job)
    word = Word.objects.create(word="Ofenhandschuh", singular_article=1)
    _link(unit_1, word)
    _link(unit_2, word)

    resource = WordExportResource(for_profession=job)

    assert resource.dehydrate_units(word) == "Backofen | Küchengeräte"


@pytest.mark.django_db()
def test_dehydrate_units_without_a_profession_lists_all_units() -> None:
    """Without a ``for_profession`` scope, every unit the word belongs to is
    still listed — this is the pre-existing, unscoped fallback behaviour."""
    job_a = Job.objects.create(name="Bäcker/-in")
    job_b = Job.objects.create(name="Kfz-Mechatroniker/-in")
    unit_a = Unit.objects.create(title="Backofen")
    unit_a.jobs.add(job_a)
    unit_b = Unit.objects.create(title="Bremsen")
    unit_b.jobs.add(job_b)
    word = Word.objects.create(word="Schraubenzieher", singular_article=1)
    _link(unit_a, word)
    _link(unit_b, word)

    resource = WordExportResource()

    assert resource.dehydrate_units(word) == "Backofen | Bremsen"
