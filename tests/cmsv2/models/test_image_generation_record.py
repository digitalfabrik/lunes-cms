"""
Tests for the prompt and model stored with a generated image (#1145).
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from unittest import mock

import pytest
from django.core.files.base import ContentFile
from django.db.models import ProtectedError

from lunes_cms.cmsv2.models import ImagePrompt, Unit
from lunes_cms.cmsv2.models import unit as unit_module
from lunes_cms.cmsv2.models import UnitWordRelation, Word
from lunes_cms.cmsv2.models import word as word_module
from lunes_cms.cmsv2.models.static import ImageSource


@pytest.fixture(autouse=True)
def _bypass_webp_conversion() -> Generator[None, None, None]:
    """
    The tests save dummy bytes as images, which Pillow can't convert.
    """
    with (
        mock.patch.object(word_module, "convert_image_to_webp", lambda _: False),
        mock.patch.object(unit_module, "convert_image_to_webp", lambda _: False),
    ):
        yield


def _generated(instance: Word | UnitWordRelation) -> ImagePrompt:
    """
    Store a generated image with its prompt and model on ``instance``.
    """
    prompt = ImagePrompt.get_default()
    instance.image.save("generated.webp", ContentFile(b"generated"), save=False)
    instance.image_prompt = prompt
    instance.image_model = "image-model"
    instance.save(image_source=ImageSource.AI_LABELED)
    return prompt


def _word() -> Word:
    return Word.objects.create(word="Hammer", singular_article=1)


def _relation() -> UnitWordRelation:
    return UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Werkzeuge"), word=_word()
    )


@pytest.mark.django_db
@pytest.mark.parametrize("make", [_word, _relation])
def test_a_generated_image_keeps_its_prompt_and_model(
    make: Callable[[], Word | UnitWordRelation],
) -> None:
    instance = make()
    prompt = _generated(instance)

    instance.refresh_from_db()
    assert instance.image_prompt == prompt
    assert instance.image_model == "image-model"


@pytest.mark.django_db
@pytest.mark.parametrize("make", [_word, _relation])
def test_uploading_an_image_forgets_the_prompt_and_model(
    make: Callable[[], Word | UnitWordRelation],
) -> None:
    instance = make()
    _generated(instance)

    instance.image.save("upload.webp", ContentFile(b"upload"), save=False)
    instance.save()

    instance.refresh_from_db()
    assert instance.image_prompt is None
    assert instance.image_model == ""


@pytest.mark.django_db
@pytest.mark.parametrize("make", [_word, _relation])
def test_removing_the_image_forgets_the_prompt_and_model(
    make: Callable[[], Word | UnitWordRelation],
) -> None:
    instance = make()
    _generated(instance)

    instance.image = None
    instance.save()

    instance.refresh_from_db()
    assert instance.image_prompt is None
    assert instance.image_model == ""


@pytest.mark.django_db
@pytest.mark.parametrize("make", [_word, _relation])
def test_saving_other_fields_keeps_the_prompt_and_model(
    make: Callable[[], Word | UnitWordRelation],
) -> None:
    instance = make()
    prompt = _generated(instance)

    instance.save()

    instance.refresh_from_db()
    assert instance.image_prompt == prompt


@pytest.mark.django_db
def test_a_prompt_images_were_generated_with_cannot_be_deleted() -> None:
    word = _word()
    prompt = ImagePrompt.objects.create(name="Anderer", prompt="{{ word }}")
    word.image.save("generated.webp", ContentFile(b"generated"), save=False)
    word.image_prompt = prompt
    word.save(image_source=ImageSource.AI_LABELED)

    with pytest.raises(ProtectedError):
        prompt.delete()
