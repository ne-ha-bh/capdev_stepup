from django.db import models

class Participant(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15, null=True)
    primary_skill = models.CharField(max_length=255, null=True)

    class Meta:
        db_table = 'participants'

class Batch(models.Model):
    batch_no = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'batches'

class Level(models.Model):
    level_no = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'levels'

class Subject(models.Model):
    subject_name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'subjects'

class Attempt(models.Model):
    attempt_no = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'attempts'

class TestResult(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE)
    invite_time = models.DateTimeField()
    test_status = models.CharField(max_length=255, null=True)
    submitted_date = models.DateTimeField(null=True)
    cn_rating = models.FloatField(null=True)
    appeared_in_test = models.CharField(max_length=3)  # To store "Yes" or "No"
    submitted_reason = models.CharField(max_length=255, null=True)
    test_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'test_results'
