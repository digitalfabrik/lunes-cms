# Generated by Django 3.2.18 on 2023-07-16 11:02

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration file to add new field example sentence
    """

    dependencies = [
        ("cms", "0010_sponsor_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="example_sentence",
            field=models.TextField(blank=True, verbose_name="example sentence"),
        ),
    ]
