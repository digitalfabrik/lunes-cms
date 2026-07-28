import pytest
from django.test.client import Client

from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.models.unit import UnitWordRelation


def _published_word(**overrides: str) -> tuple[Unit, Word]:
    """
    A word the public API will actually serve.
    """
    word = Word.objects.create(singular_article=3, **overrides)
    Word.objects.filter(pk=word.pk).update(
        audio_check_status=CheckStatus.CONFIRMED,
        image_check_status=CheckStatus.CONFIRMED,
    )
    job = Job.objects.create(name="Bäcker/-in", released=True)
    unit = Unit.objects.create(title="Backwaren", released=True)
    unit.jobs.add(job)
    UnitWordRelation.objects.create(unit=unit, word=word)
    return unit, word


@pytest.mark.django_db()
def test_unit_words_endpoint_exposes_pronunciation() -> None:
    unit, _ = _published_word(word="Baiser", pronunciation="Bessee")

    response = Client().get(f"/api/v2/units/{unit.pk}/words/")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["word"] == "Baiser"
    assert payload[0]["pronunciation"] == "Bessee"


@pytest.mark.django_db()
def test_unit_words_endpoint_returns_empty_string_without_a_variant() -> None:
    """The app should never have to handle null for this field."""
    unit, _ = _published_word(word="Hammer")

    response = Client().get(f"/api/v2/units/{unit.pk}/words/")

    assert response.status_code == 200
    assert response.json()[0]["pronunciation"] == ""


@pytest.mark.django_db()
def test_words_endpoint_exposes_pronunciation() -> None:
    _, word = _published_word(word="Niveau", pronunciation="Niwoh")

    response = Client().get(f"/api/v2/words/{word.pk}/")

    assert response.status_code == 200
    assert response.json()["pronunciation"] == "Niwoh"
