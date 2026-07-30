from django.db import migrations


# pylint: disable=unused-argument
def backfill_not_checked(apps, schema_editor):
    """
    Existing rows may have a check-status column left as NULL (e.g. words
    imported before issue #917 was fixed). The admin's check-status dropdown
    has no option for NULL, so it silently falls back to displaying its
    first choice ("Confirmed") - fix this by making the "nothing to check
    yet" state explicit as NOT_CHECKED everywhere.

    :param apps: The configuration of installed applications
    :type apps: ~django.apps.registry.Apps

    :param schema_editor: The database abstraction layer that creates actual SQL code
    :type schema_editor: ~django.db.backends.base.schema.BaseDatabaseSchemaEditor
    """
    Word = apps.get_model("cmsv2", "Word")
    UnitWordRelation = apps.get_model("cmsv2", "UnitWordRelation")

    Word.objects.filter(audio_check_status__isnull=True).update(
        audio_check_status="NOT_CHECKED"
    )
    Word.objects.filter(image_check_status__isnull=True).update(
        image_check_status="NOT_CHECKED"
    )
    Word.objects.filter(example_sentence_check_status__isnull=True).update(
        example_sentence_check_status="NOT_CHECKED"
    )
    UnitWordRelation.objects.filter(image_check_status__isnull=True).update(
        image_check_status="NOT_CHECKED"
    )
    UnitWordRelation.objects.filter(example_sentence_check_status__isnull=True).update(
        example_sentence_check_status="NOT_CHECKED"
    )


class Migration(migrations.Migration):
    """
    Migration file to backfill NULL check-status columns with NOT_CHECKED.
    """

    dependencies = [
        ("cmsv2", "0028_word_pronunciation"),
    ]

    operations = [
        migrations.RunPython(backfill_not_checked, migrations.RunPython.noop),
    ]
