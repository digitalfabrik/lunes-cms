from django.db import migrations


class Migration(migrations.Migration):
    """
    Migration to add permssions for ImageReview model
    """

    dependencies = [
        ("cmsv2", "0021_add_review_models"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="imagereview",
            options={
                "ordering": ["-created_at"],
                "permissions": [
                    ("can_review_images", "Can review and approve images"),
                    ("can_suggest_images", "Can suggest alternative images"),
                ],
                "verbose_name": "Image Review",
                "verbose_name_plural": "Image Reviews",
            },
        ),
    ]
