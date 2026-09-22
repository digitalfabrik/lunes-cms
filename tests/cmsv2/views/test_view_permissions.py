"""
Tests that the admin endpoints check model permissions and the area of the user.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from lunes_cms.cmsv2 import urls as cmsv2_urls
from lunes_cms.cmsv2.models import AlternativeWord, Area, Job, Unit, Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.views import (
    generate_example_sentence,
    word_generate_audio,
    word_generate_example_sentence_audio,
)

from tests.cmsv2.helpers import PermissionClient

unitword_sentence_audio = import_module(
    "lunes_cms.cmsv2.views.unitword_generate_example_sentence_audio"
)

pytestmark = pytest.mark.django_db


def _endpoint_urls(
    url_kwargs: dict[str, int] | None = None,
) -> list[tuple[str | None, str]]:
    """
    Every url the cmsv2 urlconf serves, with its name.

    Without ``url_kwargs`` each argument gets a placeholder. With them, only the
    urls that name an object are returned, pointed at those objects, and an
    unknown kwarg name raises ``KeyError``.
    """
    return [
        (
            pattern.name,
            reverse(
                f"cmsv2:{pattern.name}",
                kwargs={
                    name: url_kwargs[name] if url_kwargs else 1
                    for name in pattern.pattern.regex.groupindex
                },
            ),
        )
        for pattern in cmsv2_urls.urlpatterns
        if url_kwargs is None or pattern.pattern.regex.groupindex
    ]


@pytest.fixture(name="word")
def fixture_word() -> Word:
    return Word.objects.create(word="Brötchen", singular_article=3)


@pytest.fixture(name="unitword")
def fixture_unitword(word: Word) -> UnitWordRelation:
    unit = Unit.objects.create(title="Frühstück")
    return UnitWordRelation.objects.create(unit=unit, word=word)


def test_word_endpoint_denies_user_without_word_permission(
    client_with_permissions: Callable[..., Client], word: Word
) -> None:
    url = reverse("cmsv2:update_word_image_check_status", args=[word.pk])

    response = client_with_permissions("view_word").post(
        url, {"image_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 403
    assert response.json()["status"] == "error"
    word.refresh_from_db()
    assert word.image_check_status == CheckStatus.NOT_CHECKED


def test_word_endpoint_allows_user_with_word_permission(
    client_with_permissions: Callable[..., Client], word: Word
) -> None:
    url = reverse("cmsv2:update_word_image_check_status", args=[word.pk])

    response = client_with_permissions("change_word").post(
        url, {"image_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_unitword_endpoint_denies_word_only_permission(
    client_with_permissions: Callable[..., Client],
    unitword: UnitWordRelation,
) -> None:
    """Changing words does not imply changing their unit-specific data."""
    url = reverse("cmsv2:update_unitword_image_check_status", args=[unitword.pk])

    response = client_with_permissions("change_word").post(
        url, {"image_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 403


def test_job_icon_endpoint_denies_user_without_job_permission(
    client_with_permissions: Callable[..., Client],
) -> None:
    job = Job.objects.create(name="Bäcker")
    url = reverse("cmsv2:update_job_icon", args=[job.pk])

    response = client_with_permissions("change_word").post(url)

    assert response.status_code == 403


def test_unit_icon_endpoint_denies_user_without_unit_permission(
    client_with_permissions: Callable[..., Client],
) -> None:
    unit = Unit.objects.create(title="Frühstück")
    url = reverse("cmsv2:update_unit_icon", args=[unit.pk])

    response = client_with_permissions("change_word").post(url)

    assert response.status_code == 403


def test_image_generation_accepts_either_content_permission(
    client_with_permissions: Callable[..., Client],
) -> None:
    """The shared image generation endpoint serves word and unit-word editors."""
    url = reverse("cmsv2:generate_image_via_openai")

    assert client_with_permissions("view_word").post(url).status_code == 403
    assert client_with_permissions("change_word").post(url).status_code != 403
    assert (
        client_with_permissions("change_unitwordrelation").post(url).status_code != 403
    )


def test_csv_import_denies_user_without_add_permission(
    client_with_permissions: Callable[..., Client],
) -> None:
    response = client_with_permissions("change_word").get(reverse("cmsv2:import_csv"))

    assert response.status_code == 403


def test_every_endpoint_requires_login(client: Client) -> None:
    """No cmsv2 endpoint is reachable without logging in."""
    reachable = [
        url for _, url in _endpoint_urls() if client.post(url).status_code != 302
    ]

    assert not reachable, (
        "These cmsv2 endpoints served content outside the user's area. Resolve "
        "their object through an areas.visible_* accessor, not a bare manager."
    )


def test_every_endpoint_enforces_csrf(db: None) -> None:
    """No cmsv2 endpoint accepts a post without a CSRF token."""
    superuser = User.objects.create_superuser("csrf-probe", "probe@example.com", "pw")
    strict_client = Client(enforce_csrf_checks=True)
    strict_client.force_login(superuser)

    accepted = [
        url for _, url in _endpoint_urls() if strict_client.post(url).status_code != 403
    ]

    assert not accepted


_ENDPOINTS_WITHOUT_URL_OBJECT = {
    "import_csv",
    "generate_image_via_openai",
    "save_alternative_word",
}

_SWEEP_PAYLOAD = {
    "action": "delete",
    "image_check_status": CheckStatus.CONFIRMED,
    "audio_check_status": CheckStatus.CONFIRMED,
    "example_sentence": "Ein Satz.",
    "example_sentence_text": "Ein Satz.",
    "temp_filename": "nothing.png",
    "temp_audio_filename": "nothing.mp3",
}


@dataclass
class AreaContent:
    """A job/unit/word/relation/alternative-word tree, all of it in one area."""

    job: Job
    unit: Unit
    word: Word
    unitword: UnitWordRelation
    alternative_word: AlternativeWord

    def url_kwargs(self) -> dict[str, int]:
        return {
            "job_id": self.job.pk,
            "unit_id": self.unit.pk,
            "word_id": self.word.pk,
            "unitword_id": self.unitword.pk,
            "alternative_word_id": self.alternative_word.pk,
        }


def _area_content(name: str, area: Area | None) -> AreaContent:
    """
    Build a tree of content belonging to the given area.

    The word is linked to the unit and created by somebody else, so its area is
    derived from the unit rather than from the creator exception.
    """
    job = Job.objects.create(name=f"{name} job", area=area)
    unit = Unit.objects.create(title=f"{name} unit")
    unit.jobs.add(job)
    word = Word.objects.create(
        word=f"{name} word",
        singular_article=1,
        created_by_user=User.objects.create_user(f"author-of-{name}"),
    )
    return AreaContent(
        job=job,
        unit=unit,
        word=word,
        unitword=UnitWordRelation.objects.create(unit=unit, word=word),
        alternative_word=AlternativeWord.objects.create(
            word=word, alt_word=f"{name} alternative"
        ),
    )


@pytest.fixture(name="sweep_client")
def fixture_sweep_client(
    client_with_permissions: Callable[..., PermissionClient],
) -> PermissionClient:
    """
    A client holding every content permission these endpoints ask for.
    """
    return client_with_permissions(
        "change_word",
        "change_unit",
        "change_job",
        "change_unitwordrelation",
        "add_word",
        "add_unit",
    )


@pytest.fixture(name="sweep_isolation")
def fixture_sweep_isolation(media_dirs: tuple[Path, Path]) -> Iterator[None]:
    """Keep the sweep off the network; ``media_dirs`` keeps it off the real media."""
    with (
        mock.patch.object(
            generate_example_sentence,
            "openai_example_sentence",
            return_value="Ein Satz.",
        ),
        mock.patch.object(
            word_generate_audio, "openai_word_audio_bytes", return_value=b"audio"
        ),
        mock.patch.object(
            word_generate_example_sentence_audio,
            "openai_sentence_audio_bytes",
            return_value=b"audio",
        ),
        mock.patch.object(
            unitword_sentence_audio,
            "openai_sentence_audio_bytes",
            return_value=b"audio",
        ),
    ):
        yield


def test_every_endpoint_without_a_url_object_is_listed() -> None:
    """Every endpoint that names no object in its url is listed as an exception."""
    nameless = {
        pattern.name
        for pattern in cmsv2_urls.urlpatterns
        if not pattern.pattern.regex.groupindex
    }

    assert nameless == _ENDPOINTS_WITHOUT_URL_OBJECT, (
        "A cmsv2 endpoint that names no object in its url cannot be covered by "
        "the area sweep below. Give it a test of its own, like the ones for "
        "save_alternative_word, and then list it here."
    )


@pytest.mark.parametrize(
    ("content_area_name", "probe_area_name"),
    [
        pytest.param("Kolping", None, id="main-app-manager-against-an-area"),
        pytest.param(None, "Kolping", id="area-admin-against-the-main-app"),
        pytest.param("Kolping", "Telc", id="area-admin-against-another-area"),
    ],
)
def test_every_object_endpoint_is_area_scoped(
    sweep_client: PermissionClient,
    sweep_isolation: None,
    content_area_name: str | None,
    probe_area_name: str | None,
) -> None:
    """
    Holding the model permission is not enough to reach content of another area.

    Only objects named in the url are reached; a view that takes an object out
    of the request body needs a test of its own.
    """
    content_area = (
        Area.objects.create(name=content_area_name) if content_area_name else None
    )
    content = _area_content("target", content_area)

    client = sweep_client
    if probe_area_name:
        Area.objects.create(name=probe_area_name).admins.add(client.user)

    reachable = [
        name
        for name, url in _endpoint_urls(content.url_kwargs())
        if client.post(url, _SWEEP_PAYLOAD).status_code != 404
    ]

    assert not reachable, (
        "These cmsv2 endpoints reached content outside the area of the user. "
        "Resolve their object through an areas.visible_* accessor."
    )


def test_every_object_endpoint_serves_its_own_area(
    sweep_client: PermissionClient, sweep_isolation: None
) -> None:
    """
    Every object endpoint serves the content of the user's own area.
    """
    content = _area_content("main", None)
    client = sweep_client

    missing = [
        name
        for name, url in _endpoint_urls(content.url_kwargs())
        if client.post(url, _SWEEP_PAYLOAD).status_code == 404
    ]

    assert not missing, (
        "These cmsv2 endpoints refused content of the user's own area, so the "
        "sweep above would pass even without any scoping."
    )


def test_save_alternative_word_rejects_a_foreign_alternative_word(
    sweep_client: PermissionClient,
) -> None:
    """A foreign alternative word named in the body is not editable."""
    content = _area_content("foreign", Area.objects.create(name="Foreign"))

    response = sweep_client.post(
        reverse("cmsv2:save_alternative_word"),
        {
            "alternative_word_id": content.alternative_word.pk,
            "alt_word": "Übernommen",
        },
    )

    assert response.status_code == 404
    content.alternative_word.refresh_from_db()
    assert content.alternative_word.alt_word == "foreign alternative"


def test_save_alternative_word_rejects_a_foreign_word(
    sweep_client: PermissionClient,
) -> None:
    """An alternative word cannot be created on a foreign word."""
    content = _area_content("foreign", Area.objects.create(name="Foreign"))

    response = sweep_client.post(
        reverse("cmsv2:save_alternative_word"),
        {"word_id": content.word.pk, "alt_word": "Angehängt"},
    )

    assert response.status_code == 404
    assert not AlternativeWord.objects.filter(
        word=content.word, alt_word="Angehängt"
    ).exists()


def test_foreign_word_is_rejected_before_the_payload_is_validated(
    sweep_client: PermissionClient, sweep_isolation: None
) -> None:
    """The area check runs before the endpoint looks at what was posted."""
    content = _area_content("foreign", Area.objects.create(name="Foreign"))
    url = reverse(
        "cmsv2:word_generate_example_sentence_audio_via_openai", args=[content.word.pk]
    )

    response = sweep_client.post(url)

    assert response.status_code == 404


@pytest.mark.parametrize("field", ["alternative_word_id", "word_id"])
def test_save_alternative_word_rejects_a_non_numeric_id(
    sweep_client: PermissionClient, field: str
) -> None:
    """Both ids come from the body, so neither may crash on a non-numeric value."""
    response = sweep_client.post(
        reverse("cmsv2:save_alternative_word"), {field: "abc", "alt_word": "Variante"}
    )

    assert response.status_code == 404


_HTML_404_ENDPOINTS = {
    "import_csv_for_job",
    "unitword_generate_image",
    "unitword_store_generated_image_permanently",
    "unitword_generate_example_sentence_audio",
    "unitword_store_generated_example_sentence_audio_permanently",
}


def test_endpoints_the_admin_javascript_calls_deny_in_json(
    sweep_client: PermissionClient, sweep_isolation: None
) -> None:
    """
    The AJAX endpoints answer an out-of-area object with JSON.

    The admin JavaScript reads the message of the response, so an HTML body
    would surface to the editor as a JSON parser error.
    """
    content = _area_content("foreign", Area.objects.create(name="Foreign"))

    html = [
        name
        for name, url in _endpoint_urls(content.url_kwargs())
        if name not in _HTML_404_ENDPOINTS
        and "application/json"
        not in sweep_client.post(
            url, _SWEEP_PAYLOAD, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )["Content-Type"]
    ]

    assert not html, (
        "These cmsv2 endpoints answered an AJAX caller with a non-JSON body. "
        "Return decorators.json_not_found() instead of raising Http404."
    )
