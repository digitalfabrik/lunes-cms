"""
Tests for the "Analyse" sidebar entries - "Open duplicates" and "Accepted
duplicates" (issue #531).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import AcceptedWordDuplicate, Word


def _staff_client(*, with_can_view_duplicates: bool = False) -> Client:
    """A logged-in staff user who is *not* a superuser, optionally with the
    ``can_view_duplicates`` permission (issue #531)."""
    user = get_user_model().objects.create_user(
        username=f"staff-{with_can_view_duplicates}", password="password", is_staff=True
    )
    if with_can_view_duplicates:
        user.user_permissions.add(
            Permission.objects.get(
                codename="can_view_duplicates", content_type__app_label="analysis"
            )
        )
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db()
def test_admin_index_shows_no_count_without_duplicates(admin_client: Client) -> None:
    response = admin_client.get(reverse("admin:index"))

    content = response.content.decode()
    assert "Open duplicates (" not in content


@pytest.mark.django_db()
def test_admin_index_shows_duplicate_count_in_sidebar(admin_client: Client) -> None:
    # A distinctive, nonsense word text: the shared session-scoped fixture
    # data (tests/conftest.py's `load_test_data`) persists real vocabulary
    # across the whole test session without a per-test rollback, so a common
    # German word here would risk colliding with it.
    Word.objects.create(word="Flimmerquastenzange", singular_article=1)
    Word.objects.create(word="Flimmerquastenzange", singular_article=1)

    response = admin_client.get(reverse("admin:index"))

    content = response.content.decode()
    assert "Open duplicates (1)" in content


@pytest.mark.django_db()
def test_sidebar_entry_redirects_to_analysis_page(admin_client: Client) -> None:
    response = admin_client.get(
        reverse("admin:analysis_duplicatedvocabulary_changelist")
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("cmsv2:duplicated_vocabulary")


@pytest.mark.django_db()
def test_admin_index_shows_analysis_section(admin_client: Client) -> None:
    # LANGUAGE_CODE defaults to "en" and the test client doesn't request a
    # different locale, so this renders the English source strings; German
    # translations aren't covered here (like the rest of the test suite),
    # just by the separate check-translations CI job.
    response = admin_client.get(reverse("admin:index"))

    content = response.content.decode()
    assert "Analysis" in content
    assert "Open duplicates" in content
    assert "Accepted duplicates" in content


@pytest.mark.django_db()
def test_accepted_duplicates_sidebar_link_uses_pretty_url(
    admin_client: Client,
) -> None:
    """Django names a model's admin URL after its class - no hyphens
    possible - so the sidebar link is overridden to a nicer-looking one
    instead (issue #531)."""
    response = admin_client.get(reverse("admin:index"))

    content = response.content.decode()
    assert reverse("cmsv2:accepted_duplicates") in content
    assert 'href="/en/admin/analysis/acceptedduplicates/"' not in content


@pytest.mark.django_db()
def test_accepted_duplicates_changelist_lists_accepted_groups(
    admin_client: Client,
) -> None:
    word = Word.objects.create(word="Flimmerquastenzange", singular_article=1)
    accepted = AcceptedWordDuplicate.objects.create()
    accepted.words.set([word])

    # The pretty URL delegates straight to the same changelist view, so it
    # must behave identically to the auto-generated admin URL.
    response = admin_client.get(reverse("cmsv2:accepted_duplicates"))

    assert response.status_code == 200
    assert "Flimmerquastenzange" in response.content.decode()


@pytest.mark.django_db()
def test_accepted_duplicates_shows_shared_word_text_only_once(
    admin_client: Client,
) -> None:
    """Every ``Word`` in an accepted group has the same text by definition
    - the list must show it once, not "(der) X, (der) X" (issue #531)."""
    a = Word.objects.create(word="Flimmerquastenzange", singular_article=1)
    b = Word.objects.create(word="Flimmerquastenzange", singular_article=1)
    accepted = AcceptedWordDuplicate.objects.create()
    accepted.words.set([a, b])

    response = admin_client.get(reverse("cmsv2:accepted_duplicates"))

    content = response.content.decode()
    # The word legitimately appears twice on the page (once in the visible
    # column, once in the row checkbox's aria-label) - the point is that
    # neither place repeats it for each of the two underlying Word rows.
    assert "Flimmerquastenzange, Flimmerquastenzange" not in content
    assert "Flimmerquastenzange" in content


@pytest.mark.django_db()
def test_accepted_duplicates_pretty_url_denies_staff_without_permission() -> None:
    client = _staff_client()

    response = client.get(reverse("cmsv2:accepted_duplicates"))

    assert response.status_code == 302


@pytest.mark.django_db()
def test_accepted_duplicates_pretty_url_allows_staff_with_permission() -> None:
    """Not just superusers - any staff user granted ``can_view_duplicates``
    (e.g. Vokabelverwaltung, Partnermanagement) gets in too (issue #531)."""
    client = _staff_client(with_can_view_duplicates=True)

    response = client.get(reverse("cmsv2:accepted_duplicates"))

    assert response.status_code == 200


@pytest.mark.django_db()
def test_undo_accepted_duplicates_action_deletes_selected(
    admin_client: Client,
) -> None:
    accepted = AcceptedWordDuplicate.objects.create()

    response = admin_client.post(
        reverse("admin:analysis_acceptedduplicates_changelist"),
        {
            "action": "undo_accepted_duplicates",
            "_selected_action": [str(accepted.pk)],
        },
        follow=True,
    )

    assert not AcceptedWordDuplicate.objects.filter(pk=accepted.pk).exists()
    messages = [str(m) for m in response.context["messages"]]
    assert any("undone" in m for m in messages)


@pytest.mark.django_db()
def test_accepted_duplicates_changelist_offers_undo_not_delete(
    admin_client: Client,
) -> None:
    """The default "Delete selected ..." action is replaced by the
    relabelled undo action, not offered alongside it (issue #531)."""
    AcceptedWordDuplicate.objects.create()

    response = admin_client.get(reverse("cmsv2:accepted_duplicates"))

    content = response.content.decode()
    assert "Undo selected accepted duplicates" in content
    assert "Delete selected" not in content


@pytest.mark.django_db()
def test_accepted_duplicates_can_be_deleted_to_undo(admin_client: Client) -> None:
    """Deleting an accepted-duplicate entry is how you undo it - the group
    then reappears under "Open duplicates" again."""
    accepted = AcceptedWordDuplicate.objects.create()

    response = admin_client.post(
        reverse("admin:analysis_acceptedduplicates_delete", args=[accepted.pk]),
        {"post": "yes"},
    )

    assert response.status_code == 302
    assert not AcceptedWordDuplicate.objects.filter(pk=accepted.pk).exists()


@pytest.mark.django_db()
def test_accepted_duplicates_cannot_be_added_manually(admin_client: Client) -> None:
    response = admin_client.get(reverse("admin:analysis_acceptedduplicates_add"))

    assert response.status_code == 403


@pytest.mark.django_db()
def test_accepted_duplicates_denies_staff_without_permission() -> None:
    client = _staff_client()

    response = client.get(reverse("admin:analysis_acceptedduplicates_changelist"))

    # Unlike the custom views (can_view_duplicates_required -> redirect to
    # login), this is a regular ModelAdmin: a failed permission check raises
    # PermissionDenied, which Django turns into a plain 403.
    assert response.status_code == 403


@pytest.mark.django_db()
def test_accepted_duplicates_allows_staff_with_permission() -> None:
    client = _staff_client(with_can_view_duplicates=True)

    response = client.get(reverse("admin:analysis_acceptedduplicates_changelist"))

    assert response.status_code == 200
