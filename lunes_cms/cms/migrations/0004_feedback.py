# Generated by Django 3.2.13 on 2022-06-13 08:20

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration file to enable feedback
    """

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cms", "0003_remove_documentimage_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="Feedback",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "object_id",
                    models.PositiveIntegerField(
                        help_text="The id of the object this feedback entry refers to.",
                        verbose_name="object id",
                    ),
                ),
                ("comment", models.TextField(verbose_name="comment")),
                (
                    "created_date",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="The time and date when the feedback was submitted.",
                        verbose_name="submitted on",
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        help_text="The content type this feedback entry refers to.",
                        limit_choices_to=models.Q(
                            ("app_label", "cms"),
                            ("model__in", ["discipline", "trainingset", "document"]),
                        ),
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                        verbose_name="content type",
                    ),
                ),
                (
                    "read_by",
                    models.ForeignKey(
                        blank=True,
                        help_text=(
                            "The user who marked this feedback as read. If the feedback"
                            " is unread, this field is empty."
                        ),
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="feedback",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="marked as read by",
                    ),
                ),
            ],
            options={
                "verbose_name": "feedback",
                "verbose_name_plural": "feedback entries",
            },
        ),
    ]
