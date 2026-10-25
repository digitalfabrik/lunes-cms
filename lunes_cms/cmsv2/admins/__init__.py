from .area_admin import AreaAdmin
from .feedback_admin import FeedbackAdmin
from .job_admin import JobAdmin
from .notification_admin import NotificationAdmin
from .permission_labels import LunesGroupAdmin
from .review_admin import ReviewAdmin
from .unit_admin import UnitAdmin, UnitWordRelationAdmin
from .user_admin import LunesUserAdmin
from .word_admin import WordAdmin

__all__ = [
    "AreaAdmin",
    "JobAdmin",
    "WordAdmin",
    "UnitAdmin",
    "UnitWordRelationAdmin",
    "FeedbackAdmin",
    "ReviewAdmin",
    "NotificationAdmin",
    "LunesUserAdmin",
    "LunesGroupAdmin",
]
