from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add analytics event
    """

    initial = True

    dependencies: list[migrations.Migration] = []

    operations: list[migrations.operations.base.Operation] = [
        migrations.CreateModel(
            name="AnalyticsEvent",
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
                ("installation_id", models.CharField(db_index=True, max_length=255)),
                ("event_type", models.CharField(db_index=True, max_length=100)),
                ("timestamp", models.DateTimeField()),
                ("payload", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["installation_id", "event_type"],
                        name="analytics_a_install_354de4_idx",
                    ),
                    models.Index(
                        fields=["timestamp"], name="analytics_a_timesta_aef2a5_idx"
                    ),
                ],
            },
        ),
    ]
