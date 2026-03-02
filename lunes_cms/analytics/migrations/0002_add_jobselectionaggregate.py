import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0001_initial"),
        ("cmsv2", "0018_unitwordrelation_example_sentence_check_status_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobSelectionAggregate",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("selection_count", models.IntegerField()),
                ("date", models.DateField(db_index=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="selection_aggregates",
                        to="cmsv2.job",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["job", "date"], name="analytics_j_job_id_671340_idx"
                    )
                ],
            },
        ),
    ]
