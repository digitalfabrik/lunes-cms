import django.db.models.deletion
from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


# pylint: disable=unused-argument
def delete_reviews(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """
    Delete all reviews so the new column can be added as non-null.

    A word can belong to several units, so there is no unambiguous relation to
    migrate an existing review to. Reviews are not in use yet, so the existing
    ones can simply be discarded.
    """
    apps.get_model("cmsv2", "Review").objects.all().delete()


class Migration(migrations.Migration):
    """Make reviews reference a unit-word relation instead of a word"""

    dependencies = [
        ("cmsv2", "0031_remove_alternative_word_permissions"),
    ]

    operations = [
        migrations.RunPython(delete_reviews, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="review",
            name="unique_review_assignment",
        ),
        migrations.RemoveField(
            model_name="review",
            name="word",
        ),
        migrations.AddField(
            model_name="review",
            name="unit_word",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="review_assignments",
                to="cmsv2.unitwordrelation",
                verbose_name="word",
            ),
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.UniqueConstraint(
                fields=("unit_word", "reviewer"), name="unique_review_assignment"
            ),
        ),
    ]
