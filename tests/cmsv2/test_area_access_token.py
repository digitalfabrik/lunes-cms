"""
Tests for the access tokens that grant a client the content of an area.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils.timezone import now

from lunes_cms.cmsv2.models import Area, AreaAccessToken, AreaCode
from lunes_cms.cmsv2.models.area_access_token import hash_token


@pytest.fixture(name="code")
def code_fixture() -> AreaCode:
    """A code of an area that can be redeemed."""
    area = Area.objects.create(name="Kolping")
    return AreaCode.objects.create(area=area, code="TESTCODE1234")


@pytest.mark.django_db()
def test_issue_returns_a_token_for_the_area_of_the_code(code: AreaCode) -> None:
    """Redeeming a code creates a token for the area of that code."""
    access_token, token = AreaAccessToken.issue(code)

    assert token
    assert access_token.area == code.area
    assert access_token.code == code
    assert not access_token.revoked


@pytest.mark.django_db()
def test_only_the_hash_of_a_token_is_stored(code: AreaCode) -> None:
    """The plaintext of a token must not end up in the database."""
    access_token, token = AreaAccessToken.issue(code)

    access_token.refresh_from_db()
    assert access_token.token_hash == hash_token(token)
    assert token not in [str(value) for value in vars(access_token).values()]
    assert access_token.token_prefix == token[:8]


@pytest.mark.django_db()
def test_resolve_finds_the_token(code: AreaCode) -> None:
    """A token that was handed out resolves to its own row."""
    access_token, token = AreaAccessToken.issue(code)

    assert AreaAccessToken.resolve(token) == access_token


@pytest.mark.django_db()
def test_resolve_ignores_unknown_and_revoked_tokens(code: AreaCode) -> None:
    """An unknown or revoked token does not resolve."""
    access_token, token = AreaAccessToken.issue(code)

    assert AreaAccessToken.resolve("nothing-like-a-token") is None

    access_token.revoked = True
    access_token.save()
    assert AreaAccessToken.resolve(token) is None


@pytest.mark.django_db()
def test_issuing_again_keeps_the_previous_token_of_an_installation(
    code: AreaCode,
) -> None:
    """
    Issuing a token never revokes another one.

    Registration is unauthenticated, so an installation is only a label the
    client chose and must not be able to withdraw anybody's access.
    """
    first, first_token = AreaAccessToken.issue(code, installation_id="installation-1")
    _second, second_token = AreaAccessToken.issue(
        code, installation_id="installation-1"
    )

    first.refresh_from_db()
    assert not first.revoked
    assert AreaAccessToken.resolve(first_token) is not None
    assert AreaAccessToken.resolve(second_token) is not None


@pytest.mark.django_db()
def test_issuing_without_an_installation_keeps_the_previous_token(
    code: AreaCode,
) -> None:
    """Clients that send no installation cannot revoke each other."""
    _first, first_token = AreaAccessToken.issue(code)
    _second, second_token = AreaAccessToken.issue(code)

    assert AreaAccessToken.resolve(first_token) is not None
    assert AreaAccessToken.resolve(second_token) is not None


@pytest.mark.django_db()
def test_an_installation_can_hold_tokens_of_two_areas(code: AreaCode) -> None:
    """The same installation can be registered with two areas at once."""
    other_area = Area.objects.create(name="Other")
    other_code = AreaCode.objects.create(area=other_area, code="OTHERCODE123")
    _first, first_token = AreaAccessToken.issue(code, installation_id="installation-1")

    _second, second_token = AreaAccessToken.issue(
        other_code, installation_id="installation-1"
    )

    first_resolved = AreaAccessToken.resolve(first_token)
    second_resolved = AreaAccessToken.resolve(second_token)
    assert first_resolved is not None and first_resolved.area == code.area
    assert second_resolved is not None and second_resolved.area == other_area


@pytest.mark.django_db()
def test_touch_writes_the_timestamp_at_most_once_a_day(code: AreaCode) -> None:
    """Using a token does not cause a write on every single request."""
    access_token, _token = AreaAccessToken.issue(code)

    access_token.touch()
    first_use = access_token.last_used_at
    assert first_use is not None

    access_token.touch()
    assert access_token.last_used_at == first_use

    access_token.last_used_at = now() - timedelta(days=2)
    access_token.save(update_fields=["last_used_at"])
    access_token.touch()
    assert access_token.last_used_at > first_use


@pytest.mark.django_db()
def test_touching_a_deleted_token_does_not_raise(code: AreaCode) -> None:
    """
    A token that is withdrawn while it is being used is not a server error.

    The row can be gone between resolving the token and touching it, and the
    client is owed the 401 that follows, not a 500.
    """
    access_token, _token = AreaAccessToken.issue(code)
    AreaAccessToken.objects.filter(pk=access_token.pk).delete()

    access_token.touch()

    assert not AreaAccessToken.objects.exists()


@pytest.mark.django_db()
def test_deleting_a_code_withdraws_its_tokens(code: AreaCode) -> None:
    """Withdrawing a code cuts off the clients that redeemed it."""
    _access_token, token = AreaAccessToken.issue(code)

    code.delete()

    assert AreaAccessToken.resolve(token) is None
    assert not AreaAccessToken.objects.exists()


@pytest.mark.django_db()
def test_deleting_a_code_keeps_the_tokens_of_the_other_codes(code: AreaCode) -> None:
    """The codes of an area can be withdrawn one by one."""
    other_code = AreaCode.objects.create(area=code.area, code="SECONDCODE12")
    _first, first_token = AreaAccessToken.issue(code)
    _second, second_token = AreaAccessToken.issue(other_code)

    code.delete()

    assert AreaAccessToken.resolve(first_token) is None
    assert AreaAccessToken.resolve(second_token) is not None
