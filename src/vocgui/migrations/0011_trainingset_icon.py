# Generated by Django 3.1.5 on 2021-01-16 18:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vocgui', '0010_discipline_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingset',
            name='icon',
            field=models.ImageField(blank=True, upload_to='images/'),
        ),
    ]
