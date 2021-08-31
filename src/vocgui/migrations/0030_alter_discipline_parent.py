# Generated by Django 3.2.3 on 2021-08-31 08:56

from django.db import migrations
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('vocgui', '0029_auto_20210721_1141'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discipline',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='vocgui.discipline', verbose_name='parent'),
        ),
    ]
