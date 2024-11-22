from rest_framework.views import exception_handler
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Extend the default exception_handler of rest_framework.
    Purpose: Simplify testing by ensuring that the detail message is the same for all 404 responses.
    """

    response = exception_handler(exc, context)

    if response.status_code == status.HTTP_404_NOT_FOUND:
        response.data["detail"] = "Not found."

    return response
