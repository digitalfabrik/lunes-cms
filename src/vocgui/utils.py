"""
A collection of helper methods and classes
"""

import os
import uuid
import pathlib


def create_ressource_path(parent_dir, filename):
    """
    Create a file path with a uuid and given parent directory.
    """
    return os.path.join(parent_dir, str(uuid.uuid1()) + pathlib.Path(filename).suffix)

def document_to_string(doc):
    """
    Create string representation of a document object
    """
    alt_words = [str(elem) for elem in doc.alternatives.all()]
    
    if len(alt_words) > 0:
        alt_words = "(" + ", ".join(alt_words) + ")"
        return "(" + doc.get_article_display() + ") " + doc.word + " " + alt_words
    else:
        return "(" + doc.get_article_display() + ") " + doc.word
