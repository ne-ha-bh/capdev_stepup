# Generated by Django 4.2 on 2025-02-11 07:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stepup_api', '0007_attempt_batch_level_subject_testresult_and_more'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='attempt',
            table='attempts',
        ),
        migrations.AlterModelTable(
            name='batch',
            table='batches',
        ),
        migrations.AlterModelTable(
            name='level',
            table='levels',
        ),
        migrations.AlterModelTable(
            name='participant',
            table='participants',
        ),
        migrations.AlterModelTable(
            name='subject',
            table='subjects',
        ),
        migrations.AlterModelTable(
            name='testresult',
            table='test_results',
        ),
    ]
