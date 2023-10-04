from . import content_type, group
from .alternative_word import AlternativeWord
from .discipline import Discipline
from .document import Document
from .document_image import DocumentImage
from .feedback import Feedback
from .group_api_key import GroupAPIKey
from .sponsor import Sponsor
from .static import Static, convert_umlaute_audio, convert_umlaute_images
from .training_set import TrainingSet

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
    "Feedback",
    "Sponsor",
]
