# Generated by Django 3.1.5 on 2021-01-16 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vocgui', '0009_auto_20201104_2030'),
    ]

    operations = [
        migrations.AddField(
            model_name='discipline',
            name='icon',
            field=models.ImageField(blank=True, upload_to='images/'),
        ),
    ]
