from django.db import migrations


class Migration(migrations.Migration):
    """Add the ``can_view_analytics`` custom permission to ``SessionDurationReport``."""

    dependencies = [
        ("analytics", "0009_sessiondurationreport"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="sessiondurationreport",
            options={
                "permissions": [("can_view_analytics", "Can view analytics")],
                "proxy": True,
                "verbose_name": "Total Session Duration",
                "verbose_name_plural": "Total Session Duration",
            },
        ),
    ]
