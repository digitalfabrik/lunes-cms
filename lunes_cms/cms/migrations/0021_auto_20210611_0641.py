# Generated by Django 3.2.2 on 2021-06-11 06:41

from django.db import migrations, models
import lunes_cms.cms.models
import lunes_cms.cms.validators


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0020_alter_document_creation_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discipline',
            name='icon',
            field=models.ImageField(blank=True, upload_to=lunes_cms.cms.models.convert_umlaute_images, verbose_name='icon'),
        ),
        migrations.AlterField(
            model_name='document',
            name='audio',
            field=models.FileField(blank=True, null=True, upload_to=lunes_cms.cms.models.convert_umlaute_audio, validators=[lunes_cms.cms.validators.validate_file_extension, lunes_cms.cms.validators.validate_file_size, lunes_cms.cms.validators.validate_multiple_extensions], verbose_name='audio'),
        ),
        migrations.AlterField(
            model_name='documentimage',
            name='image',
            field=models.ImageField(upload_to=lunes_cms.cms.models.convert_umlaute_images, validators=[lunes_cms.cms.validators.validate_multiple_extensions]),
        ),
        migrations.AlterField(
            model_name='trainingset',
            name='icon',
            field=models.ImageField(blank=True, upload_to=lunes_cms.cms.models.convert_umlaute_images, verbose_name='icon'),
        ),
    ]
