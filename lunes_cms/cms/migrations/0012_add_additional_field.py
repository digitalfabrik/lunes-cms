# Generated by Django 3.2.21 on 2024-02-16 09:57

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration file to add new field example sentence
    """

    dependencies = [
        ("cms", "0011_document_example_sentence"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="additional_meaning_1",
            field=models.CharField(
                blank=True,
                max_length=256,
                null=True,
                verbose_name="additional meaning 1",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="additional_meaning_2",
            field=models.CharField(
                blank=True,
                max_length=256,
                null=True,
                verbose_name="additional meaning 2",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="definition",
            field=models.TextField(
                blank=True, max_length=256, null=True, verbose_name="definition"
            ),
        ),
    ]