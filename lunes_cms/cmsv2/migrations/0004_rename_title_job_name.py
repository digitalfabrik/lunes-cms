from django.db import migrations


class Migration(migrations.Migration):
    """
    Migration to rename the 'title' field to 'name' in the Job model.
    """

    dependencies = [
        ("cmsv2", "0003_alter_job_created_by_alter_unit_created_by_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="job",
            old_name="title",
            new_name="name",
        ),
    ]
