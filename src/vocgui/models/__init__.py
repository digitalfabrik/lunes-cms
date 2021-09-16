from .alternative_word import AlternativeWord
from .discipline import Discipline
from .document import Document
from .document_image import DocumentImage
from .static import Static, convert_umlaute_images, convert_umlaute_audio
from .training_set import TrainingSet
from . import group

__all__ = [
    "AlternativeWord",
    "Discipline",
    "Document",
    "DocumentImage",
    "Static",
    "TrainingSet",
    "convert_umlaute_images",
    "convert_umlaute_images",
    "group",
]
