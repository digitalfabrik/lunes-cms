"""
Register models for Django's CRUD back end and
specify autocomplete_fields, search_fields and nested modules
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from .admins import JobAdmin, WordAdmin, UnitAdmin
from .models import Job, Word, Unit


admin.site.register(Job, JobAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(Word, WordAdmin)
