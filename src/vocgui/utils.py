"""
A collection of helper methods and classes
"""

import os
import uuid
import string
import pathlib
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _


def create_ressource_path(parent_dir, filename):
    """Create a file path with a uuid and given parent directory.

    :param parent_dir: parent directory
    :type parent_dir: str
    :param filename: file name
    :type filename: str
    :return: full file path
    :rtype: str
    """
    return os.path.join(parent_dir, str(uuid.uuid1()) + pathlib.Path(filename).suffix)


def get_random_key(length: int = 10, excluded_chars: list = []) -> str:
    """Auxiliary function that creates a random key based on latin letters and digits using
    the passed length. Optionally, it is possible to exclude characters like l and 1.

    :param length: key length, defaults to 10
    :type length: int, optional
    :param excluded_chars: list of characters to be excluded (mixed dtypes possible), defaults to []
    :type excluded_chars: list, optional
    :return: key
    :rtype: str
    """
    choices = string.ascii_letters + string.digits
    for char in excluded_chars:
        choices = choices.replace(str(char), "")
    key = get_random_string(length, choices)
    return key


def document_to_string(doc):
    """Create string representation of a document object

    :param doc: Document object
    :type doc: models.Document
    :return: String representation of document image
    :rtype: str
    """
    alt_words = [str(elem) for elem in doc.alternatives.all()]

    if len(alt_words) > 0:
        alt_words = "(" + ", ".join(alt_words) + ")"
        return "(" + doc.get_article_display() + ") " + doc.word + " " + alt_words
    else:
        return "(" + doc.get_article_display() + ") " + doc.word


def get_child_count(disc):
    """Returns the number of children of a discipline.
    Every child contains at least one training set or is a direct/indirect
    parent of a discipline that contains one.

    :param disc: Discipline instance
    :type disc: models.Discipline
    :return: sum of children
    :rtype: int
    """
    children_counter = 0
    for child in disc.get_children():
        if child.released and get_training_set_count(child) > 0:
            children_counter += 1
    return children_counter


def get_training_set_count(disc):
    """Returns the total number of training sets of a discipline and all its
    child elements.

    :param disc: Discipline instance
    :type disc: models.Discipline
    :return: sum of training sets
    :rtype: int
    """
    training_set_counter = 0
    for child in disc.get_descendants(include_self=True):
        training_set_counter += child.training_sets.count()
    return training_set_counter


def get_key(request, keyword="Api-Key"):
    """Retrieve API Key from Authorization header of http request.
    Optionally, a custom keyword can be specified. The function
    espects the key to be delivered as follows:
    {"Authorization": "<keyword> <api-key>}

    :param request: get request
    :type request: HttpRequest
    :param keyword: keyword for api key in authorization header, defaults to "Api-Key"
    :type keyword: str, optional
    :return: api key in authorization header
    :rtype: str
    """
    authorization = request.META.get("HTTP_AUTHORIZATION")
    if not authorization:
        return None
    try:
        _, key = authorization.split("{} ".format(keyword))
    except ValueError:
        key = None
    return key


def iter_to_string(iter):
    """
    Convert an iterable of objects to a readable string.
    It joins the first elements with commas and separates the last element by "and".

    :param iter: The input iterable
    :type iter: ~collections.abc.Iterable

    :return: The joined list
    :rtype: str
    """
    # Convert iterable to list to support querysets etc.
    lst = list(iter)
    # If the list contains more than 1 element, save the last element for later
    last_element = lst.pop() if len(lst) > 1 else None
    # Join remaining elements with commas and surrounding quotes
    list_str = '"' + '", "'.join(map(str, lst)) + '"'
    # Append the last element with "and"
    if last_element:
        list_str += " " + _("and") + f' "{last_element}"'
    # Return final string
    return list_str
