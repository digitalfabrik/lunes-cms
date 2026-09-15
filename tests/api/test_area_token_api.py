"""
API tests for redeeming the code of an area and for the content a client sees
once it sends the access token it received.
"""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test.client import Client
from rest_framework.throttling import SimpleRateThrottle

from lunes_cms.cms.models import GroupAPIKey
from lunes_cms.cmsv2.models import Area, AreaAccessToken, AreaCode, Job

from .area_content import (
    JOBS_ENDPOINT,
    REGISTER_ENDPOINT,
    released_unit_with_word,
    UNITS_ENDPOINT,
    WORDS_ENDPOINT,
)


@pytest.fixture(autouse=True)
def reset_throttling():
    """
    Empty the throttle cache around every test.

    The registration endpoint is throttled per client address, and all tests
    come from the same address, so without this they would throttle each other.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(name="area")
def area_fixture():
    """An area with a code, a released job, a unit and a word."""
    area = Area.objects.create(name="Kolping")
    AreaCode.objects.create(area=area, code="KOLPING12345")
    job = Job.objects.create(name="Area job", released=True, area=area)
    unit, word = released_unit_with_word(job, "Area unit", "Bereichswort")
    return SimpleNamespace(area=area, job=job, unit=unit, word=word)


@pytest.fixture(name="main_app")
def main_app_fixture():
    """A released job of the main app with a unit and a word."""
    job = Job.objects.create(name="Main job", released=True)
    unit, word = released_unit_with_word(job, "Main unit", "Hauptwort")
    return SimpleNamespace(job=job, unit=unit, word=word)


def register(code="KOLPING12345", **payload):
    """
    Redeem a code and return the response.

    :param code: The code to redeem
    :param payload: Further fields to send
    :return: The response of the registration endpoint
    """
    return Client().post(
        REGISTER_ENDPOINT,
        data={"code": code, **payload},
        content_type="application/json",
    )


def token_client(token):
    """
    A client that sends the given access token with every request.

    :param token: The access token to send
    :return: The prepared test client
    """
    return Client(HTTP_AUTHORIZATION=f"Api-Key {token}")


def registered_client(code="KOLPING12345"):
    """
    Redeem a code and return a client that uses the resulting token.

    :param code: The code to redeem
    :return: The prepared test client
    """
    response = register(code)
    assert response.status_code == 201, response.content
    return token_client(response.json()["token"])


#
# Registration
#


@pytest.mark.django_db()
def test_registration_returns_a_token_and_the_area(area):
    """Redeeming a valid code registers the client and hands out a token."""
    response = register()

    assert response.status_code == 201
    body = response.json()
    assert body["token"]
    assert body["area"] == {"id": area.area.pk, "name": "Kolping"}
    assert AreaAccessToken.objects.count() == 1


@pytest.mark.django_db()
def test_registration_stores_the_installation(area):
    """The installation a client sends is stored with its token."""
    response = register(installation_id="installation-1")

    assert response.status_code == 201
    assert AreaAccessToken.objects.get().installation_id == "installation-1"


@pytest.mark.django_db()
def test_registration_normalizes_the_code(area):
    """A code that was typed off a printout is normalized before it is looked up."""
    response = register(code="  kolping12345 ")

    assert response.status_code == 201
    assert response.json()["area"]["name"] == "Kolping"


@pytest.mark.django_db()
def test_registration_rejects_an_unknown_code(area):
    """An unknown code is answered with a recognizable error."""
    response = register(code="NOSUCHCODE12")

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_area_code"
    assert not AreaAccessToken.objects.exists()


@pytest.mark.django_db()
def test_registration_rejects_a_missing_code(area):
    """A request without a code is a bad request, not a server error."""
    response = Client().post(
        REGISTER_ENDPOINT, data={}, content_type="application/json"
    )

    assert response.status_code == 400
    assert response.json()["code"] == ["This field is required."]


@pytest.mark.django_db()
def test_registration_does_not_store_the_token_in_the_clear(area):
    """The token exists in the answer only, the database keeps its hash."""
    token = register().json()["token"]

    stored = AreaAccessToken.objects.get()
    assert token not in str(vars(stored))
    assert stored.token_prefix == token[:8]


@pytest.mark.django_db()
def test_registering_again_does_not_cut_off_the_earlier_token(area):
    """
    A second registration must not revoke the token of the first one.

    Registration is unauthenticated and the installation is whatever the client
    sent, so revoking by installation would let anybody with a code knock a
    known client offline.
    """
    first = register(installation_id="installation-1").json()["token"]
    second = register(installation_id="installation-1").json()["token"]

    assert token_client(first).get(JOBS_ENDPOINT).status_code == 200
    assert token_client(second).get(JOBS_ENDPOINT).status_code == 200


@pytest.mark.django_db()
def test_registration_is_throttled(area, monkeypatch):
    """
    Codes cannot be guessed by trying them out in a loop.

    The rate is lowered to a single request, because the REST framework binds
    the rates to the throttle class when it is imported, so ``override_settings``
    would not reach them.
    """
    monkeypatch.setitem(
        SimpleRateThrottle.THROTTLE_RATES, "area_registration", "1/hour"
    )

    assert register().status_code == 201
    assert register().status_code == 429


#
# Content of an area
#


@pytest.mark.django_db()
def test_jobs_of_the_area_are_listed_for_a_registered_client(area, main_app):
    """With a token, the job list is the job list of the area."""
    response = registered_client().get(JOBS_ENDPOINT)

    assert response.status_code == 200
    returned_ids = {job["id"] for job in response.json()}
    assert returned_ids == {area.job.pk}


@pytest.mark.django_db()
def test_units_and_words_of_the_area_are_served(area, main_app):
    """With a token, the units and words below an area job are readable."""
    client = registered_client()

    units = client.get(f"{JOBS_ENDPOINT}{area.job.pk}/units/")
    job_words = client.get(f"{JOBS_ENDPOINT}{area.job.pk}/words/")
    unit_words = client.get(f"{UNITS_ENDPOINT}{area.unit.pk}/words/")
    words = client.get(WORDS_ENDPOINT)

    assert units.status_code == 200
    assert {unit["id"] for unit in units.json()} == {area.unit.pk}
    assert units.json()[0]["number_words"] == 1
    assert job_words.status_code == 200
    assert {word["id"] for word in job_words.json()} == {area.word.pk}
    assert unit_words.status_code == 200
    assert len(unit_words.json()) == 1
    assert words.status_code == 200
    assert {word["id"] for word in words.json()} == {area.word.pk}


@pytest.mark.django_db()
def test_main_app_content_is_hidden_from_a_registered_client(area, main_app):
    """A token answers with the content of its area instead of the main app."""
    client = registered_client()

    jobs = client.get(JOBS_ENDPOINT)
    job = client.get(f"{JOBS_ENDPOINT}{main_app.job.pk}/")
    units = client.get(f"{JOBS_ENDPOINT}{main_app.job.pk}/units/")
    job_words = client.get(f"{JOBS_ENDPOINT}{main_app.job.pk}/words/")
    unit_words = client.get(f"{UNITS_ENDPOINT}{main_app.unit.pk}/words/")

    assert main_app.job.pk not in {returned["id"] for returned in jobs.json()}
    assert job.status_code == 404
    assert units.status_code in (403, 404)
    assert job_words.status_code in (403, 404)
    assert unit_words.status_code in (403, 404)
    assert main_app.word.pk not in {
        word["id"] for word in client.get(WORDS_ENDPOINT).json()
    }


@pytest.mark.django_db()
def test_the_content_of_another_area_stays_hidden(area):
    """A token of one area does not open the content of another one."""
    other_area = Area.objects.create(name="Other")
    AreaCode.objects.create(area=other_area, code="OTHERCODE123")
    other_job = Job.objects.create(name="Other job", released=True, area=other_area)
    other_unit, other_word = released_unit_with_word(other_job, "Other", "Fremdwort")
    client = registered_client()

    jobs = client.get(JOBS_ENDPOINT)
    units = client.get(f"{JOBS_ENDPOINT}{other_job.pk}/units/")
    job_words = client.get(f"{JOBS_ENDPOINT}{other_job.pk}/words/")
    unit_words = client.get(f"{UNITS_ENDPOINT}{other_unit.pk}/words/")
    words = client.get(WORDS_ENDPOINT)

    assert other_job.pk not in {returned["id"] for returned in jobs.json()}
    assert units.status_code in (403, 404)
    assert job_words.status_code in (403, 404)
    assert unit_words.status_code in (403, 404)
    assert other_word.pk not in {word["id"] for word in words.json()}


@pytest.mark.django_db()
def test_an_unreleased_job_of_the_area_stays_hidden(area):
    """A token does not publish content the area itself has not released yet."""
    draft = Job.objects.create(name="Draft", released=False, area=area.area)
    draft_unit, _word = released_unit_with_word(draft, "Draft unit", "Entwurf")
    client = registered_client()

    jobs = client.get(JOBS_ENDPOINT)
    units = client.get(f"{JOBS_ENDPOINT}{draft.pk}/units/")
    unit_words = client.get(f"{UNITS_ENDPOINT}{draft_unit.pk}/words/")

    assert draft.pk not in {job["id"] for job in jobs.json()}
    assert units.status_code in (403, 404)
    assert unit_words.status_code in (403, 404)


@pytest.mark.django_db()
def test_an_archived_job_of_the_area_stays_hidden(area):
    """Archiving a job of an area takes it off the API, just like in the main app."""
    area.job.archived = True
    area.job.save()

    response = registered_client().get(JOBS_ENDPOINT)

    assert area.job.pk not in {job["id"] for job in response.json()}


#
# Invalid tokens
#


@pytest.mark.django_db()
def test_an_unknown_token_is_an_error_on_every_endpoint(area, main_app):
    """A token that cannot be resolved is never silently ignored."""
    client = token_client("not-a-real-token")

    for url in (
        JOBS_ENDPOINT,
        f"{JOBS_ENDPOINT}{main_app.job.pk}/units/",
        f"{JOBS_ENDPOINT}{main_app.job.pk}/words/",
        f"{UNITS_ENDPOINT}{main_app.unit.pk}/words/",
        WORDS_ENDPOINT,
    ):
        response = client.get(url)
        assert response.status_code == 401, url
        assert response.json()["error"] == "invalid_area_token"


@pytest.mark.django_db()
def test_a_revoked_token_is_an_error(area):
    """Revoking a token cuts the client off."""
    client = registered_client()
    assert client.get(JOBS_ENDPOINT).status_code == 200

    AreaAccessToken.objects.update(revoked=True)

    assert client.get(JOBS_ENDPOINT).status_code == 401


@pytest.mark.django_db()
def test_deleting_the_code_cuts_off_its_clients(area):
    """Withdrawing a code takes the access of everybody who redeemed it."""
    client = registered_client()
    assert client.get(JOBS_ENDPOINT).status_code == 200

    AreaCode.objects.filter(code="KOLPING12345").delete()

    assert client.get(JOBS_ENDPOINT).status_code == 401


@pytest.mark.django_db()
def test_another_authorization_keyword_is_treated_as_no_token(area, main_app):
    """A header with another keyword is not read as a token at all."""
    client = Client(HTTP_AUTHORIZATION="Bearer SOMETHINGELSE")

    response = client.get(JOBS_ENDPOINT)

    assert response.status_code == 200
    returned_ids = {job["id"] for job in response.json()}
    assert main_app.job.pk in returned_ids
    assert area.job.pk not in returned_ids


@pytest.mark.django_db()
def test_a_group_api_key_of_the_v1_api_is_rejected(area, main_app):
    """
    The v2 API shares the ``Api-Key`` keyword with the v1 API.

    A group API key of the v1 API therefore reaches this authentication and
    does not resolve, which is an error like any other unresolvable token. The
    v1 endpoints are unaffected, they never see this authentication class.
    """
    group = Group.objects.create(name="Some group")
    api_key = GroupAPIKey.objects.create(group=group)

    response = Client(HTTP_AUTHORIZATION=f"Api-Key {api_key.token}").get(JOBS_ENDPOINT)

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_area_token"


@pytest.mark.django_db()
def test_a_keyword_without_a_token_is_treated_as_no_token(area, main_app):
    """An empty header is answered with the main app, not with an error."""
    response = Client(HTTP_AUTHORIZATION="Api-Key").get(JOBS_ENDPOINT)

    assert response.status_code == 200
    returned_ids = {job["id"] for job in response.json()}
    assert main_app.job.pk in returned_ids
    assert area.job.pk not in returned_ids


#
# Endpoints that are the same for everybody
#


@pytest.mark.django_db()
def test_sponsors_and_feedback_are_not_scoped(area):
    """Endpoints that publish no content of an area are untouched by the token."""
    client = registered_client()

    assert client.get("/api/v2/sponsors/").status_code == 200
    assert (
        Client().get("/api/v2/sponsors/").json()
        == client.get("/api/v2/sponsors/").json()
    )


#
# Broken data must not leak across areas
#
# ``validate_unit_jobs`` forbids a unit of an area job to have any other job,
# but it only runs in the admin form. A CSV import, a data migration or a shell
# session can write what the admin would refuse, so the API rejects it as well.
#


@pytest.mark.django_db()
def test_a_unit_shared_between_two_areas_is_published_to_neither(area):
    """A unit that hangs off two areas belongs to neither of them."""
    other_area = Area.objects.create(name="Other")
    AreaCode.objects.create(area=other_area, code="OTHERCODE123")
    other_job = Job.objects.create(name="Other job", released=True, area=other_area)
    area.unit.jobs.add(other_job)

    for code, job in (("KOLPING12345", area.job), ("OTHERCODE123", other_job)):
        client = registered_client(code)
        units = client.get(f"{JOBS_ENDPOINT}{job.pk}/units/")
        unit_words = client.get(f"{UNITS_ENDPOINT}{area.unit.pk}/words/")
        words = client.get(WORDS_ENDPOINT)

        assert units.status_code == 200, code
        assert area.unit.pk not in {unit["id"] for unit in units.json()}, code
        assert unit_words.status_code in (403, 404), code
        assert words.status_code == 200, code
        assert area.word.pk not in {word["id"] for word in words.json()}, code


@pytest.mark.django_db()
def test_a_released_job_of_another_area_does_not_release_a_unit(area):
    """
    The released job and the job of the area have to be the same job.

    Every ``filter()`` over the jobs of a unit opens a join of its own, so a
    unit on a released job of area A and an unreleased job of area B must not
    reach the client of area B through the released job of area A.
    """
    other_area = Area.objects.create(name="Other")
    AreaCode.objects.create(area=other_area, code="OTHERCODE123")
    draft = Job.objects.create(name="Other draft", released=False, area=other_area)
    area.unit.jobs.add(draft)

    client = registered_client("OTHERCODE123")
    unit_words = client.get(f"{UNITS_ENDPOINT}{area.unit.pk}/words/")
    words = client.get(WORDS_ENDPOINT)

    assert unit_words.status_code in (403, 404)
    assert area.word.pk not in {word["id"] for word in words.json()}
