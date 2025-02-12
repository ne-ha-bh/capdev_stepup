from django.db import models

class Participant(models.Model):
    participant_id = models.AutoField(primary_key=True, db_column='ParticipantID')  # Primary key
    name = models.CharField(max_length=255, db_column='Name')
    email = models.EmailField(unique=True, db_column='Email')
    primary_skill = models.CharField(max_length=255, null=True, db_column='PrimarySkill')

    class Meta:
        db_table = 'participants'

class Batch(models.Model):
    batch_id = models.AutoField(primary_key=True, db_column='BatchID')  # Primary key
    batch_no = models.CharField(max_length=255, unique=True, db_column='BatchNo')

    class Meta:
        db_table = 'batches'

class Subject(models.Model):
    subject_id = models.AutoField(primary_key=True, db_column='SubjectID')  # Primary key
    subject_name = models.CharField(max_length=255, unique=True, db_column='SubjectName')

    class Meta:
        db_table = 'subjects'

class Level(models.Model):
    level_id = models.AutoField(primary_key=True, db_column='LevelID')  # Primary key
    level_no = models.CharField(max_length=255, unique=True, db_column='LevelNo')

    class Meta:
        db_table = 'levels'

class Attempt(models.Model):
    attempt_id = models.AutoField(primary_key=True, db_column='AttemptID')  # Primary key
    attempt_no = models.CharField(max_length=255, unique=True, db_column='AttemptNo')

    class Meta:
        db_table = 'attempts'

class TestResult(models.Model):
    test_result_id = models.AutoField(primary_key=True, db_column='TestResultID')  # Primary key
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, db_column='ParticipantID')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, db_column='BatchID')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, db_column='SubjectID')
    level = models.ForeignKey(Level, on_delete=models.CASCADE, db_column='LevelID')
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, db_column='AttemptID')
    invite_time = models.DateTimeField(db_column='InviteTime')
    test_status = models.CharField(max_length=255, null=True, db_column='TestStatus')
    submitted_date = models.DateTimeField(null=True, db_column='SubmittedDate')
    cn_rating = models.FloatField(null=True, db_column='CNRating')
    appeared_in_test = models.BooleanField(null=True, db_column='AppearedInTest')
    submitted_reason = models.CharField(max_length=255, null=True)
    test_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'test_results'

class User(models.Model):
    id = models.AutoField(primary_key=True)  # Primary Key
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    class Meta:
        db_table = 'users'
