"""
Register models for Django's CRUD back end and
specify autocomplete_fields, search_fields and nested modules
"""

from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.contrib.auth.models import User

from .admins import FeedbackAdmin, JobAdmin, ReviewAdmin, LunesUserAdmin, UnitAdmin, WordAdmin
from .models import Feedback, Job, Unit, UnitWordRelation, Word

admin.site.register(Job, JobAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(Word, WordAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.unregister(User)
admin.site.register(User, LunesUserAdmin)
admin.site.register(UnitWordRelation, ReviewAdmin)
