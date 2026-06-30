"""
Content Management System for the Lunes Vocabulary Trainer App
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lunes-cms")
except PackageNotFoundError:
    __version__ = "unknown"
