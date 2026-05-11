from django.db import migrations


class Migration(migrations.Migration):
    """Creates a proxy model for showing aggregated image review counts per unit-word relation in admin."""

    dependencies = [
        ("cmsv2", "0022_alter_imagereview_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImageReviewSummary",
            fields=[],
            options={
                "verbose_name": "Image Review",
                "verbose_name_plural": "Image Reviews",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("cmsv2.unitwordrelation",),
        ),
    ]
