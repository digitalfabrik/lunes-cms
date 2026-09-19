import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration file to add the access tokens of an area.
    """

    dependencies = [
        ("cmsv2", "0034_areacode"),
    ]

    operations = [
        migrations.CreateModel(
            name="AreaAccessToken",
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
                    "token_hash",
                    models.CharField(
                        editable=False,
                        max_length=64,
                        unique=True,
                        verbose_name="token hash",
                    ),
                ),
                (
                    "token_prefix",
                    models.CharField(
                        editable=False,
                        help_text="The first characters of the token. The token itself is only known to the client it was handed to.",
                        max_length=8,
                        verbose_name="token",
                    ),
                ),
                (
                    "installation_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=255,
                        verbose_name="installation",
                    ),
                ),
                (
                    "revoked",
                    models.BooleanField(
                        default=False,
                        help_text="A revoked token cannot be used anymore.",
                        verbose_name="revoked",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
                (
                    "last_used_at",
                    models.DateTimeField(
                        blank=True,
                        editable=False,
                        help_text="Only updated once a day, so it can be off by up to one day.",
                        null=True,
                        verbose_name="last used at",
                    ),
                ),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_tokens",
                        to="cmsv2.area",
                        verbose_name="area",
                    ),
                ),
                (
                    "code",
                    models.ForeignKey(
                        help_text="The code that was redeemed for this token. Deleting that code also withdraws this token.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_tokens",
                        to="cmsv2.areacode",
                        verbose_name="code",
                    ),
                ),
            ],
            options={
                "verbose_name": "Area access token",
                "verbose_name_plural": "Area access tokens",
                "ordering": ["-created_at"],
            },
        ),
    ]
