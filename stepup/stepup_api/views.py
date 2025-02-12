import re
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from .models import Participant, Batch, Level, Subject, Attempt, TestResult
import pandas as pd
from datetime import datetime
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils.timezone import make_aware

# def convert_to_datetime(date_str):
#     return datetime.strptime(date_str, '%A, %b %d %Y at %I:%M %p').strftime('%Y-%m-%d %H:%M:%S')
def convert_to_datetime(date_str):
    naive_datetime = datetime.strptime(date_str, '%A, %b %d %Y at %I:%M %p')
    return make_aware(naive_datetime)
def extract_attempt_no(test_name):
    match = re.search(r'Attempt\s[1-3](?:\s|$)', test_name)
    attempt_no = match.group(0).strip() if match else None
    print(f"Extracted attempt_no: {attempt_no} from test_name: {test_name}")
    return attempt_no

@api_view(['POST'])
def upload_data(request):
    file = request.FILES['file']
    print(f"Uploaded file: {file}")

    # Specify the correct sheet name
    sheet_name = "List of Engineers Invited"
    df = pd.read_excel(file, sheet_name=sheet_name)
    print(f"Reading sheet: {sheet_name}")

    # Ensure the columns are stripped of any leading/trailing spaces
    df.columns = df.columns.str.strip()
    print(f"Columns in the uploaded file: {df.columns}")

    for index, row in df.iterrows():
        print(f"Processing row: {row}")

        name = row['Name']
        email = row['Email']
        mobile = row['Mobile']
        primary_skill = row['Primary Skill']
        batch_no = row['Batch']
        level_no = row['Level']
        subject_name = row['Subjects']
        test_name = row['Test name']
        invite_time = convert_to_datetime(row['Invites Time'])
        test_status = row['Test Status'] if 'Test Status' in df.columns and pd.notna(row['Test Status']) else None
        submitted_date = convert_to_datetime(row['Submitted Date']) if pd.notna(row['Submitted Date']) else None
        cn_rating = row['CN rating'] if pd.notna(row['CN rating']) else None
        submitted_reason = row['Submitted reason'] if 'Submitted reason' in df.columns and pd.notna(row['Submitted reason']) else None
        # appeared_in_test = row['Appeared in test'] if 'Appeared in test' in df.columns and pd.notna(row['Appeared in test']) else None

        attempt_no = extract_attempt_no(test_name)
        print(f"attempt_no: {attempt_no}")

        with transaction.atomic():
            # Check if participant exists, if yes, update; if not, create
            participant, created = Participant.objects.get_or_create(email=email)
            participant.name = name
            participant.mobile = mobile
            participant.primary_skill = primary_skill
            participant.save()
            print(f"Participant: {participant}")

            batch, _ = Batch.objects.get_or_create(batch_no=batch_no)
            subject, _ = Subject.objects.get_or_create(subject_name=subject_name)
            level, _ = Level.objects.get_or_create(level_no=level_no)
            attempt, _ = Attempt.objects.get_or_create(attempt_no=attempt_no)
            print(f"Saved attempt_no in DB: {attempt.attempt_no}")
            
            print(f"Creating TestResult for participant: {participant}, batch: {batch}, subject: {subject}, level: {level}, attempt: {attempt}")
            # print(f"invite_time: {invite_time}, test_status: {test_status}, submitted_date: {submitted_date}, cn_rating: {cn_rating}, appeared_in_test: {appeared_in_test}, submitted_reason: {submitted_reason}, test_name: {test_name}")
            TestResult.objects.create(
                participant=participant,
                batch=batch,
                subject=subject,
                level=level,
                attempt=attempt,
                invite_time=invite_time,
                test_status=test_status,
                submitted_date=submitted_date,
                cn_rating=cn_rating,
                #appeared_in_test=appeared_in_test,
                submitted_reason=submitted_reason, test_name=test_name
            )

    return Response({'message': 'Data uploaded successfully'}, status=200)
