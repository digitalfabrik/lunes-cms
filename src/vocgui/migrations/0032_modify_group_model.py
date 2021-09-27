from django.db import migrations, models
import vocgui.models.static


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('vocgui', '0031_alter_discipline_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='icon',
            field=models.ImageField(blank=True, upload_to=vocgui.models.static.convert_umlaute_images, verbose_name='icon'),
        ),
    ]
    def mutate_state(self, project_state, preserve=True):
        """
        This is a workaround that allows to store ``auth``
        migration outside the directory it should be stored.
        """
        app_label = self.app_label
        self.app_label = 'auth'
        state = super(Migration, self).mutate_state(project_state, preserve)
        self.app_label = app_label
        return state

    def apply(self, project_state, schema_editor, collect_sql=False):
        """
        Same workaround as described in ``mutate_state`` method.
        """
        app_label = self.app_label
        self.app_label = 'auth'
        state = super(Migration, self).apply(project_state, schema_editor, collect_sql)
        self.app_label = app_label
        return state