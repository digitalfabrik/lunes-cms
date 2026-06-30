from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration file to get rid of magic strings and use status constants instead.
    """

    dependencies = [
        ("cmsv2", "0023_alter_unit_released"),
    ]

    operations = [
        migrations.AlterField(
            model_name="unitwordrelation",
            name="example_sentence_check_status",
            field=models.CharField(
                choices=[("CONFIRMED", "Confirmed"), ("NOT_CHECKED", "Not Checked")],
                default="NOT_CHECKED",
                max_length=20,
                null=True,
                verbose_name="example sentence check status",
            ),
        ),
        migrations.AlterField(
            model_name="unitwordrelation",
            name="image_check_status",
            field=models.CharField(
                choices=[("CONFIRMED", "Confirmed"), ("NOT_CHECKED", "Not Checked")],
                default="NOT_CHECKED",
                max_length=20,
                null=True,
                verbose_name="image check status",
            ),
        ),
        migrations.AlterField(
            model_name="word",
            name="audio_check_status",
            field=models.CharField(
                choices=[("CONFIRMED", "Confirmed"), ("NOT_CHECKED", "Not Checked")],
                default="NOT_CHECKED",
                max_length=20,
                null=True,
                verbose_name="audio check status",
            ),
        ),
        migrations.AlterField(
            model_name="word",
            name="example_sentence_check_status",
            field=models.CharField(
                choices=[("CONFIRMED", "Confirmed"), ("NOT_CHECKED", "Not Checked")],
                default="NOT_CHECKED",
                max_length=20,
                null=True,
                verbose_name="example sentence check status",
            ),
        ),
        migrations.AlterField(
            model_name="word",
            name="image_check_status",
            field=models.CharField(
                choices=[("CONFIRMED", "Confirmed"), ("NOT_CHECKED", "Not Checked")],
                default="NOT_CHECKED",
                max_length=20,
                null=True,
                verbose_name="image check status",
            ),
        ),
    ]
