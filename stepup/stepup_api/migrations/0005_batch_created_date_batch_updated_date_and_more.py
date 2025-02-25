# Generated by Django 4.2 on 2025-02-25 09:58

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stepup_api', '0004_alter_testresult_submitted_reason_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 252535, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='batch',
            name='updated_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 252559, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='level',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 252919, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='level',
            name='updated_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 252937, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='participant',
            name='batch',
            field=models.ForeignKey(blank=True, db_column='BatchID', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='stepup_api.batch'),
        ),
        migrations.AddField(
            model_name='participant',
            name='comments',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 253784, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='participant',
            name='delivery_unit',
            field=models.IntegerField(db_column='DU', null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='designation',
            field=models.CharField(db_column='Designation', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='emp_id',
            field=models.CharField(db_column='EmployeeId', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='invited_for_next_lvl',
            field=models.BooleanField(null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='is_active',
            field=models.BooleanField(null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='is_delete',
            field=models.BooleanField(null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='latest_level_passed',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='stepup_api.level'),
        ),
        migrations.AddField(
            model_name='participant',
            name='project_involvement',
            field=models.CharField(db_column='Involvement', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='project_name',
            field=models.CharField(db_column='ProjectName', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='role',
            field=models.CharField(blank=True, db_column='Role', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='secondary_skill',
            field=models.CharField(db_column='SecondrySkill', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='skill',
            field=models.CharField(db_column='Skills', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='stepup_started',
            field=models.DateTimeField(db_column='StepUp_Started', null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='total_exp',
            field=models.IntegerField(db_column='TotalExperience', null=True),
        ),
        migrations.AddField(
            model_name='participant',
            name='updated_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 253794, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='subject',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 253256, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='subject',
            name='level',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='stepup_api.level'),
        ),
        migrations.AddField(
            model_name='subject',
            name='updated_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 253268, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='testresult',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 254332, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='testresult',
            name='no_of_attempts_invited',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='testresult',
            name='updated_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 254342, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='user',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 254817, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AddField(
            model_name='user',
            name='updated_date',
            field=models.DateTimeField(default=datetime.datetime(2025, 2, 25, 9, 58, 51, 254828, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AlterField(
            model_name='testresult',
            name='appeared_in_test',
            field=models.IntegerField(db_column='AppearedInTest', null=True),
        ),
        migrations.AlterField(
            model_name='testresult',
            name='attempt',
            field=models.IntegerField(db_column='NumberOfAttempts', null=True),
        ),
        migrations.AlterField(
            model_name='testresult',
            name='test_name',
            field=models.CharField(db_column='TestName', max_length=255, null=True),
        ),
        migrations.DeleteModel(
            name='Attempt',
        ),
    ]
