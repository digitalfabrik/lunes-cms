from django.db import migrations


# pylint: disable=unused-argument
def delete_alternative_word_permissions(apps, schema_editor):
    """
    Alternative words are edited as part of their word and no longer have
    permissions of their own. Django only ever adds permissions, so the ones
    created for existing databases have to be deleted explicitly, otherwise
    they keep showing up when the permissions of a group are edited.

    :param apps: The configuration of installed applications
    :type apps: ~django.apps.registry.Apps

    :param schema_editor: The database abstraction layer that creates actual SQL code
    :type schema_editor: ~django.db.backends.base.schema.BaseDatabaseSchemaEditor
    """
    Permission = apps.get_model("auth", "Permission")

    Permission.objects.filter(
        content_type__app_label="cmsv2", content_type__model="alternativeword"
    ).delete()


class Migration(migrations.Migration):
    """
    Migration file to drop the permissions of the alternative word model.
    """

    dependencies = [
        ("auth", "0001_initial"),
        ("contenttypes", "0001_initial"),
        ("cmsv2", "0030_refactor_review"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="alternativeword",
            options={
                "default_permissions": (),
                "verbose_name": "alternative word",
                "verbose_name_plural": "alternative words",
            },
        ),
        migrations.RunPython(
            delete_alternative_word_permissions, migrations.RunPython.noop
        ),
    ]
