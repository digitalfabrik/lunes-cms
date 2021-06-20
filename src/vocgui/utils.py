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
