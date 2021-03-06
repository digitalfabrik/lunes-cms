# Generated by Django 2.2.16 on 2021-04-06 16:19

from django.db import migrations, models
import vocgui.validators


class Migration(migrations.Migration):

    dependencies = [
        ('vocgui', '0013_auto_20210325_1604'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='documentimage',
            options={'verbose_name': 'Bild', 'verbose_name_plural': 'Bilder'},
        ),
        migrations.AlterField(
            model_name='document',
            name='audio',
            field=models.FileField(upload_to='audio/', validators=[vocgui.validators.validate_file_extension, vocgui.validators.validate_file_size]),
        ),
    ]
