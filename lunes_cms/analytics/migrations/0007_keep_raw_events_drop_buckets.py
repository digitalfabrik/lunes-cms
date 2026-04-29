from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Switch the aggregation pipeline from delete-after-aggregation to a per-event
    ``aggregated_at`` watermark, and drop the duration histogram fields on
    ``SessionAggregate`` (the reports show durations in minutes/seconds directly).
    """

    dependencies = [
        ("analytics", "0006_alter_analyticsevent_event_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="analyticsevent",
            name="aggregated_at",
            field=models.DateTimeField(db_index=True, null=True),
        ),
        migrations.RemoveField(
            model_name="sessionaggregate",
            name="duration_buckets",
        ),
    ]
