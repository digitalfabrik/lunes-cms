# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration to add module_duration, session_start, and session_end as valid analytics event types
    """

    dependencies = [
        ("analytics", "0003_jobselectionaggregate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="analyticsevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("job_selected", "Job Selected"),
                    ("module_duration", "Module Duration"),
                    ("session_start", "Session Start"),
                    ("session_end", "Session End"),
                ],
                db_index=True,
                max_length=100,
            ),
        ),
    ]
