"""
This module contains the model serializers, see :doc:`django:topics/serialization`.
"""

from .alternative_word_serializer import AlternativeWordSerializer
from .area_registration_serializer import (
    AreaCodeSerializer,
    AreaInfoResponseSerializer,
    AreaRegistrationResponseSerializer,
    AreaRegistrationSerializer,
    AreaSerializer,
)
from .feedback_serializer import FeedbackSerializer
from .job_serializer import JobSerializer
from .sponsor_serializer import SponsorSerializer
from .unit_serializer import UnitSerializer
from .unit_word_relation_serializer import UnitWordRelationSerializer
from .word_serializer import WordSerializer
