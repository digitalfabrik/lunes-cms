import json

import pytest
from django.test.client import Client

from .api_config import PARAMETRIZED_API_ENDPOINTS


# pylint: disable=unused-argument
@pytest.mark.django_db()
@pytest.mark.parametrize(
    "endpoint,post_data,api_key,expected_result,expected_status_code",
    PARAMETRIZED_API_ENDPOINTS,
)
def test_api_result(
    load_test_data, endpoint, post_data, api_key, expected_result, expected_status_code
):
    """
    This test class checks all endpoints defined in :attr:`~tests.api.api_config.API_ENDPOINTS`.
    It verifies that the content delivered by the endpoint is equivalent with the data
    provided in the corresponding json file.

    :param load_test_data: The fixture providing the test data (see :meth:`~tests.conftest.load_test_data`)
    :type load_test_data: tuple

    :param endpoint: The API endpoint to test
    :type endpoint: str

    :param post_data: The post data for the request
    :type post_data: dict

    :param api_key: The API key for the request
    :type api_key: str

    :param expected_result: The path to the json file that contains the expected result
    :type expected_result: str

    :param expected_status_code: The expected HTTP status code
    :type expected_status_code: int
    """
    auth = {"HTTP_AUTHORIZATION": f"Api-Key {api_key}"} if api_key else {}
    client = Client(**auth)
    if post_data:
        response = client.post(endpoint, data=post_data, format="json")
    else:
        response = client.get(endpoint, format="json")
    print(response.headers)
    print(response.json())
    assert response.status_code == expected_status_code
    with open(expected_result, encoding="utf-8") as f:
        assert response.json() == json.load(f)
