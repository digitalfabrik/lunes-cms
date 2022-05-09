from .alternative_word import AlternativeWord
from .discipline import Discipline
from .document import Document
from .document_image import DocumentImage
from .static import Static, convert_umlaute_images, convert_umlaute_audio
from .training_set import TrainingSet
from . import group
from .group_api_key import GroupAPIKey

__all__ = [
    "AlternativeWord",
    "Discipline",
    "Document",
    "DocumentImage",
    "Static",
    "TrainingSet",
    "convert_umlaute_images",
    "convert_umlaute_audio",
    "group",
    "GroupAPIKey",
]
