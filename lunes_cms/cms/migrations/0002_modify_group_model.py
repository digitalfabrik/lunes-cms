from django.db import migrations, models

import lunes_cms.cms.models.static


class Migration(migrations.Migration):
    """
    Migration file for changing group model
    """

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("cms", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="icon",
            field=models.ImageField(
                blank=True,
                upload_to=lunes_cms.cms.models.static.convert_umlaute_images,
                verbose_name="icon",
            ),
        ),
    ]

    def mutate_state(self, project_state, preserve=True):
        """
        This is a workaround that allows to store ``auth``
        migration outside the directory it should be stored.
        Takes a ProjectState and returns a new one with the migration's operations applied to it.
        Preserves the original object state by default and will return a mutated state from a copy.
        """
        app_label = self.app_label
        self.app_label = "auth"
        state = super().mutate_state(project_state, preserve)
        self.app_label = app_label
        return state

    def apply(self, project_state, schema_editor, collect_sql=False):
        """
        Same workaround as described in ``mutate_state`` method.
        Takes a project_state representing all migrations prior to this one
        and a schema_editor for a live database and applies the migration in a forwards order.
        Returns the resulting project state for efficient re-use by following Migrations.
        """
        app_label = self.app_label
        self.app_label = "auth"
        state = super().apply(project_state, schema_editor, collect_sql)
        self.app_label = app_label
        return state
