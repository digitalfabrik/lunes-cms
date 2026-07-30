import pytest
from django.core.files.base import ContentFile

from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.models.unit import UnitWordRelation


def _word_with_audio() -> Word:
    """A confirmed word with audios for the word and an example sentence."""
    word = Word.objects.create(
        word="Baiser",
        singular_article=3,
        example_sentence="Ich backe ein Baiser.",
    )
    word.audio.save("baiser.mp3", ContentFile(b"word-audio"), save=False)
    word.example_sentence_audio.save(
        "baiser_example_sentence.mp3", ContentFile(b"sentence-audio"), save=False
    )
    word.save()
    assert word.audio_check_status == CheckStatus.NOT_CHECKED
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED

    word.audio_check_status = CheckStatus.CONFIRMED
    word.example_sentence_check_status = CheckStatus.CONFIRMED
    word.save()
    assert word.audio_check_status == CheckStatus.CONFIRMED
    assert word.example_sentence_check_status == CheckStatus.CONFIRMED
    return word


@pytest.mark.django_db()
def test_changing_pronunciation_keeps_both_recordings() -> None:
    word = _word_with_audio()
    audio_name = word.audio.name
    sentence_audio_name = word.example_sentence_audio.name
    assert audio_name and sentence_audio_name

    word.pronunciation = "Bessee"
    word.save()

    word.refresh_from_db()
    assert word.audio.name == audio_name
    assert word.audio.storage.exists(audio_name)
    assert word.example_sentence_audio.name == sentence_audio_name
    assert word.example_sentence_audio.storage.exists(sentence_audio_name)


@pytest.mark.django_db()
def test_changing_pronunciation_flags_both_recordings_for_review() -> None:
    word = _word_with_audio()

    word.pronunciation = "Bessee"
    word.save()

    word.refresh_from_db()
    assert word.audio_check_status == CheckStatus.NOT_CHECKED
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db()
def test_saving_without_touching_pronunciation_keeps_confirmed_status() -> None:
    """An unrelated edit must not create review work."""
    word = _word_with_audio()

    word.plural = "Baisers"
    word.save()

    word.refresh_from_db()
    assert word.audio_check_status == CheckStatus.CONFIRMED
    assert word.example_sentence_check_status == CheckStatus.CONFIRMED


@pytest.mark.django_db()
def test_pronunciation_change_does_not_invent_a_status_without_audio() -> None:
    """A word with no recordings has nothing to review."""
    word = Word.objects.create(word="Niveau", singular_article=3)

    word.pronunciation = "Niwoh"
    word.save()

    word.refresh_from_db()
    assert word.audio_check_status == CheckStatus.NOT_CHECKED
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db()
def test_pronunciation_change_respects_the_no_sentence_no_status_rule() -> None:
    word = Word.objects.create(word="Baiser", singular_article=3, example_sentence="")
    word.example_sentence_audio.save("stray.mp3", ContentFile(b"a"), save=False)
    word.save()

    word.pronunciation = "Bessee"
    word.save()

    word.refresh_from_db()
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db()
def test_pronunciation_change_flags_per_unit_sentence_audio() -> None:
    word = _word_with_audio()
    job = Job.objects.create(name="Bäcker/-in")
    unit = Unit.objects.create(title="Backwaren")
    unit.jobs.add(job)
    relation = UnitWordRelation.objects.create(
        unit=unit, word=word, example_sentence="Das Baiser ist fertig."
    )
    relation.example_sentence_audio.save(
        "relation_example_sentence.mp3", ContentFile(b"relation-audio"), save=False
    )
    relation.example_sentence_check_status = CheckStatus.CONFIRMED
    relation.save()
    relation_audio_name = relation.example_sentence_audio.name
    assert relation_audio_name

    word.pronunciation = "Bessee"
    word.save()

    relation.refresh_from_db()
    assert relation.example_sentence_check_status == CheckStatus.NOT_CHECKED
    assert relation.example_sentence_audio.storage.exists(relation_audio_name)


@pytest.mark.django_db()
def test_pronunciation_defaults_to_empty() -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)

    assert word.pronunciation == ""


def test_text_for_audio_generation_respells_the_term_but_keeps_the_article() -> None:
    word = Word(word="Baiser", singular_article=3, pronunciation="Bessee")

    assert word.text_for_audio_generation() == "das Bessee"


def test_text_for_audio_generation_uses_the_spelling_without_a_variant() -> None:
    word = Word(word="Hammer", singular_article=1)

    assert word.text_for_audio_generation() == "der Hammer"
