# Generated by Django 3.2.16 on 2023-05-03 14:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0009_sponsor"),
    ]

    operations = [
        migrations.AddField(
            model_name="sponsor",
            name="url",
            field=models.URLField(blank=True, verbose_name="URL"),
        ),
    ]