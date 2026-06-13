from django.urls import path

from . import admin_views

app_name = "analytics_admin"

urlpatterns = [
    path(
        "session-duration/",
        admin_views.sessions_report,
        name="sessions_report",
    ),
]
