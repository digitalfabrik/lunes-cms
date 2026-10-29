"""
Management command to notify staff about experts who are behind on reviews.

Meant to run daily, e.g. as a cronjob. An expert with reviews which are pending
for more than ``REVIEW_SLOW_EXPERT_DAYS`` days is reported to the users who
assigned these reviews, at most once in that period (see #1038).
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from lunes_cms.cmsv2.internal_notifications import notify_slow_experts


class Command(BaseCommand):
    """
    Notify staff about experts with overdue reviews.
    """

    help = "Notify staff about experts with reviews which are pending for too long"

    def handle(self, *args: Any, **options: Any) -> None:
        notifications = notify_slow_experts()
        self.stdout.write(f"Created {len(notifications)} notification(s)")
