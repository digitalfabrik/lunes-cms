# Generated by Django 3.2.13 on 2022-07-24 19:33

import django.core.validators
from django.db import migrations, models
import lunes_cms.cms.models.group_api_key


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0005_auto_create_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="groupapikey",
            name="hashed_key",
        ),
        migrations.RemoveField(
            model_name="groupapikey",
            name="prefix",
        ),
        migrations.RemoveField(
            model_name="groupapikey",
            name="id",
        ),
        migrations.AddField(
            model_name="groupapikey",
            name="id",
            field=models.AutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.RenameField(
            model_name="groupapikey",
            old_name="organization",
            new_name="group",
        ),
        migrations.AlterField(
            model_name="groupapikey",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="api_keys",
                to="auth.group",
                verbose_name="group",
            ),
        ),
        migrations.RenameField(
            model_name="groupapikey",
            old_name="name",
            new_name="token",
        ),
        migrations.AlterField(
            model_name="groupapikey",
            name="token",
            field=models.CharField(
                default=lunes_cms.cms.models.group_api_key.generate_default_token,
                help_text="10-50 characters, only digits and upper case letters allowed.",
                max_length=50,
                unique=True,
                validators=[
                    django.core.validators.MinLengthValidator(10),
                    django.core.validators.RegexValidator(
                        "^[0-9A-Z]*$", "Only digits and upper case letters allowed"
                    ),
                ],
                verbose_name="token",
            ),
        ),
        migrations.RenameField(
            model_name="groupapikey",
            old_name="created",
            new_name="creation_date",
        ),
        migrations.AlterField(
            model_name="groupapikey",
            name="creation_date",
            field=models.DateTimeField(auto_now_add=True, verbose_name="creation date"),
        ),
        migrations.AlterField(
            model_name="groupapikey",
            name="expiry_date",
            field=models.DateTimeField(
                blank=True,
                help_text="Once API key expires, clients cannot use it anymore.",
                null=True,
                verbose_name="expiration date",
            ),
        ),
        migrations.AlterField(
            model_name="groupapikey",
            name="revoked",
            field=models.BooleanField(
                blank=True,
                default=False,
                help_text="If the API key is revoked, clients cannot use it anymore.",
                verbose_name="revoked",
            ),
        ),
    ]