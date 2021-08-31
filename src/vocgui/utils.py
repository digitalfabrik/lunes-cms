"""
A collection of helper methods and classes
"""

import os
import uuid
import pathlib


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
        if get_training_set_count(child) > 0:
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
