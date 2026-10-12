import pytest
from django.core.files.base import ContentFile

from lunes_cms.cmsv2.models import Unit, UnitWordRelation, Word
from lunes_cms.cmsv2.models.static import CheckStatus


def _word_with_sentence_audio() -> Word:
    word = Word.objects.create(
        word="Baiser", singular_article=3, example_sentence="Ich backe ein Baiser"
    )
    word.example_sentence_audio.save(
        "baiser_example_sentence.mp3", ContentFile(b"sentence-audio"), save=False
    )
    word.example_sentence_check_status = CheckStatus.CONFIRMED
    word.save()
    return word


def _relation_with_sentence_audio() -> UnitWordRelation:
    word = Word.objects.create(word="Baiser", singular_article=3)
    unit = Unit.objects.create(title="Backwaren")
    relation = UnitWordRelation.objects.create(
        unit=unit, word=word, example_sentence="Das Baiser ist fertig"
    )
    relation.example_sentence_audio.save(
        "relation_example_sentence.mp3", ContentFile(b"relation-audio"), save=False
    )
    relation.example_sentence_check_status = CheckStatus.CONFIRMED
    relation.save()
    return relation


@pytest.mark.django_db()
def test_editing_word_sentence_keeps_audio_and_flags_it_for_review() -> None:
    word = _word_with_sentence_audio()
    audio_name = word.example_sentence_audio.name
    assert audio_name

    word.example_sentence = "Ich backe ein Baiser."
    word.save()

    word.refresh_from_db()
    assert word.example_sentence_audio.name == audio_name
    assert word.example_sentence_audio.storage.exists(audio_name)
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db()
def test_editing_relation_sentence_keeps_audio_and_flags_it_for_review() -> None:
    relation = _relation_with_sentence_audio()
    audio_name = relation.example_sentence_audio.name
    assert audio_name

    relation.example_sentence = "Das Baiser ist fertig."
    relation.save()

    relation.refresh_from_db()
    assert relation.example_sentence_audio.name == audio_name
    assert relation.example_sentence_audio.storage.exists(audio_name)
    assert relation.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db()
def test_saving_relation_without_sentence_change_keeps_confirmed_status() -> None:
    relation = _relation_with_sentence_audio()

    relation.save()

    relation.refresh_from_db()
    assert relation.example_sentence_check_status == CheckStatus.CONFIRMED


@pytest.mark.django_db()
def test_clearing_word_sentence_removes_its_audio() -> None:
    word = _word_with_sentence_audio()
    audio_name = word.example_sentence_audio.name
    assert audio_name

    word.example_sentence = ""
    word.save()

    word.refresh_from_db()
    assert not word.example_sentence_audio
    assert not word.example_sentence_audio.storage.exists(audio_name)
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db()
def test_clearing_relation_sentence_removes_its_audio() -> None:
    relation = _relation_with_sentence_audio()
    audio_name = relation.example_sentence_audio.name
    assert audio_name

    relation.example_sentence = "  "
    relation.save()

    relation.refresh_from_db()
    assert not relation.example_sentence_audio
    assert not relation.example_sentence_audio.storage.exists(audio_name)
    assert relation.example_sentence_check_status == CheckStatus.NOT_CHECKED
