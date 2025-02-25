from django.db import models
from django.utils import timezone

class Batch(models.Model):
    batch_id = models.AutoField(primary_key=True, db_column='BatchID')  # Primary key
    batch_no = models.CharField(max_length=255, unique=True, db_column='BatchNo')
    created_date = models.DateTimeField(default=timezone.now())
    updated_date = models.DateTimeField(default=timezone.now())

    class Meta:
        db_table = 'batches'

class Level(models.Model):
    level_id = models.AutoField(primary_key=True, db_column='LevelID')  # Primary key
    level_no = models.CharField(max_length=255, unique=True, db_column='LevelNo')
    created_date = models.DateTimeField(default=timezone.now())
    updated_date = models.DateTimeField(default=timezone.now())

    class Meta:
        db_table = 'levels'


class Subject(models.Model):
    subject_id = models.AutoField(primary_key=True, db_column='SubjectID')  # Primary key
    subject_name = models.CharField(max_length=255, unique=True, db_column='SubjectName')
    level = models.ForeignKey(Level, on_delete=models.DO_NOTHING, null=True)
    created_date = models.DateTimeField(default=timezone.now())
    updated_date = models.DateTimeField(default=timezone.now())
    class Meta:
        db_table = 'subjects'

class Participant(models.Model):
    participant_id = models.AutoField(primary_key=True, db_column='ParticipantID')  # Primary key
    name = models.CharField(max_length=255, db_column='Name')
    email = models.EmailField(unique=True, db_column='Email')
    primary_skill = models.CharField(max_length=255, null=True, db_column='PrimarySkill')
    secondary_skill = models.CharField(max_length=255, null=True, db_column='SecondrySkill')
    batch = models.ForeignKey(Batch, on_delete=models.DO_NOTHING, null=True, blank=True, db_column='BatchID')
    role = models.CharField(max_length=255, null=True, blank=True, db_column='Role')
    stepup_started = models.DateTimeField(null=True, db_column='StepUp_Started')
    delivery_unit = models.IntegerField(null=True, db_column='DU')
    project_name = models.CharField(max_length=255, null=True, db_column='ProjectName')
    emp_id = models.CharField(max_length=255, null=True, db_column='EmployeeId')
    total_exp = models.IntegerField(null=True, db_column='TotalExperience')
    skill = models.CharField(max_length=255, null=True, db_column='Skills')
    designation = models.CharField(max_length=255, null=True, db_column='Designation')
    project_involvement = models.CharField(max_length=255, null=True, db_column='Involvement')
    latest_level_passed = models.ForeignKey(Level,  on_delete=models.DO_NOTHING, null=True, blank=True)
    invited_for_next_lvl = models.BooleanField(null=True)
    is_active = models.BooleanField(null=True)
    is_delete = models.BooleanField(null=True)
    comments = models.TextField(null=True)
    created_date = models.DateTimeField(default=timezone.now())
    updated_date = models.DateTimeField(default=timezone.now())
    class Meta:
        db_table = 'participants'

class TestResult(models.Model):
    test_result_id = models.AutoField(primary_key=True, db_column='TestResultID')  # Primary key
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, db_column='ParticipantID')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, db_column='BatchID')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, db_column='SubjectID')
    level = models.ForeignKey(Level, on_delete=models.CASCADE, db_column='LevelID')
    attempt = models.IntegerField(null=True, db_column='NumberOfAttempts')
    invite_time = models.DateTimeField(db_column='InviteTime')
    test_status = models.CharField(max_length=255, null=True, db_column='TestStatus')
    submitted_date = models.DateTimeField(null=True, db_column='SubmittedDate')
    cn_rating = models.FloatField(null=True, db_column='CNRating')
    appeared_in_test = models.IntegerField(null=True, db_column='AppearedInTest') 
    submitted_reason = models.CharField(max_length=255, null=True, db_column='SubmittedReason')  
    test_name = models.CharField(max_length=255, null=True, db_column='TestName') 
    no_of_attempts_invited = models.IntegerField(null=True)
    created_date = models.DateTimeField(default=timezone.now())
    updated_date = models.DateTimeField(default=timezone.now())
    class Meta:
        db_table = 'test_results'

class User(models.Model):
    id = models.AutoField(primary_key=True)  # Primary Key
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    created_date = models.DateTimeField(default=timezone.now())
    updated_date = models.DateTimeField(default=timezone.now())

    class Meta:
        db_table = 'users'
