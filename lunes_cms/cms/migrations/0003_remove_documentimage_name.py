# Generated by Django 3.2.13 on 2022-05-21 09:49

from django.db import migrations


class Migration(migrations.Migration):
    """
    Migration file to remove documentimage field
    """

    dependencies = [
        ("cms", "0002_modify_group_model"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="documentimage",
            name="name",
        ),
    ]
