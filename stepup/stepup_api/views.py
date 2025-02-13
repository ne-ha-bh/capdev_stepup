import re
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from .models import Participant, Batch, Level, Subject, Attempt, TestResult
import pandas as pd
from datetime import datetime
from django.db.models import Count, Q, Subquery, OuterRef
from django.http import JsonResponse
from django.utils.timezone import make_aware


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
        appeared_in_test = (
                True if row['Appeared in test'].strip().lower() == 'yes' 
                else False if row['Appeared in test'].strip().lower() == 'no' 
                else None
            ) if 'Appeared in test' in df.columns and pd.notna(row['Appeared in test']) else None

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
            print(f"invite_time: {invite_time}, test_status: {test_status}, submitted_date: {submitted_date}, cn_rating: {cn_rating}, appeared_in_test: {appeared_in_test}, submitted_reason: {submitted_reason}, test_name: {test_name}")
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
                appeared_in_test=appeared_in_test,
                submitted_reason=submitted_reason, test_name=test_name
            )

    return Response({'message': 'Data uploaded successfully'}, status=200)

@api_view(['GET'])
def get_dashboard1_data(request):
    '''
    Get method to get users details on dashboards
    '''
    # Subjects to consider
    subjects = ['Core Software Engineering', 'Prompt Engineering', 'Core Software Engineering Coding Skills']

    # Invite Count Query for Level 1
    invite_count_results_level1 = get_invite_count_results("Level1")
    # expected result of above query
    #     [
    #     {'BatchID__BatchNo': 'Batch1', 'LevelID__LevelNo': 'Level1', 'InviteCount': 10},
    #     {'BatchID__BatchNo': 'Batch2', 'LevelID__LevelNo': 'Level1', 'InviteCount': 15},
    # ]

    # Invite Count Query for Level 2
    invite_count_results_level2 = get_invite_count_results("Level2") 
    # {'BatchID__BatchNo': 'Batch1', 'LevelID__LevelNo': 'Level2', 'InviteCount': 8},
    # {'BatchID__BatchNo': 'Batch2', 'LevelID__LevelNo': 'Level2', 'InviteCount': 12},
    # ]


    # Passed Count Query for Level 1
    # Get the count of distinct subjects matching the required names
    subject_count_subquery = Subject.objects.filter(SubjectName__in=subjects).distinct().count()

    # Get participants who passed all required subjects with CNRating > 4.0
    qualified_participants_subquery = TestResult.objects.filter(LevelID__LevelNo="Level1",
                    CNRating__gt=4.0, ParticipantID=OuterRef("ParticipantID") \
                ).values("ParticipantID").annotate(subject_count=Count("SubjectID", distinct=True)
                ).filter(subject_count=subject_count_subquery).values("ParticipantID")

    # Main query to count distinct participants per batch
    passed_count_results_level1 = Participant.objects.filter(
                    ParticipantID__in=Subquery(qualified_participants_subquery),
                    testresults__LevelID__LevelNo="Level1",
                    testresults__CNRating__gt=4.0) \
                .values("testresults__BatchID__BatchNo")  \
                .annotate(ParticipantCount=Count("ParticipantID", distinct=True)) \
                .order_by("testresults__BatchID__BatchNo")
    

    # Passed Count Query for Level 2
    passed_count_results_level2 = Participant.objects.filter(
            testresults__LevelID__LevelNo="Level2", 
            testresults__CNRating__gte=4).\
        values("testresults__BatchID__BatchNo") \
        .annotate(ParticipantCount=Count("ParticipantID", distinct=True)) \
        .order_by("testresults__BatchID__BatchNo")
    

    # Failed Count Query for Level 1
    failed_count_results_level1 = Participant.objects.filter(
            testresults__LevelID__LevelNo="Level1",
            testresults__CNRating__lt=4.0,
            testresults__AttemptID__AttemptNo="Attempt3").\
        values("testresults__BatchID__BatchNo") \
        .annotate(ParticipantCount=Count("ParticipantID", distinct=True)) \
        .order_by("testresults__BatchID__BatchNo")


    # Failed Count Query for Level 2
    failed_count_results_level2 = Participant.objects.filter(
            testresults__LevelID__LevelNo="Level2", 
            testresults__AttemptID__AttemptNo="Attempt3",  
            testresults__CNRating__lt=4) \
        .values("testresults__BatchID__BatchNo")  \
        .annotate(ParticipantCount=Count("ParticipantID", distinct=True)) \
        .order_by("testresults__BatchID__BatchNo")

   
    # In-Progress Count Query for Level 1
    
    # Get emails of passed candidates
    passed_candidates = Participant.objects.filter(
                testresults__LevelID__LevelNo="Level1",
                testresults__SubjectID__SubjectName__in=subjects,
                testresults__CNRating__gte=4,
                testresults__AppearedInTest=True
            ).values("Email").annotate(subject_count=Count("testresults__SubjectID", distinct=True)) \
            .filter(subject_count=3)  
    
    # Get emails of failed candidates
    failed_candidates = Participant.objects.filter(
            testresults__LevelID__LevelNo="Level1",
            testresults__SubjectID__SubjectName__in=subjects,
            testresults__AttemptID__AttemptNo="Attempt3",
            testresults__CNRating__lt=4,
            testresults__AppearedInTest=True
        ).values("Email")

    # Main Query: Find in-progress candidates
    in_progress_count_results_level1 = Participant.objects.filter(
                testresults__LevelID__LevelNo="Level1",
                testresults__SubjectID__SubjectName__in=subjects,
                testresults__AppearedInTest=True
            ).exclude(Email__in=Subquery(passed_candidates)) \
            .exclude(Email__in=Subquery(failed_candidates))  \
            .values("testresults__BatchID__BatchNo", "testresults__LevelID__LevelNo") \
            .annotate(InProgressCount=Count("ParticipantID", distinct=True)) \
            .order_by("testresults__BatchID__BatchNo", "testresults__LevelID__LevelNo")
    

    # In-Progress Count Query for Level 2
    # Get participants who are either passed (CNRating >= 4) OR failed in Attempt 3 (CNRating < 4)
    excluded_participants = TestResult.objects.filter(LevelID__LevelNo="Level2").filter(
                    Q(CNRating__gte=4) | Q(AttemptID__AttemptNo="Attempt3", CNRating__lt=4)
                ).values("ParticipantID")

    # Main Query: Find in-progress candidates
    in_progress_count_results_level2 = Participant.objects.filter(
                    testresults__LevelID__LevelNo="Level2"
                ).exclude(ParticipantID__in=Subquery(excluded_participants)) \
                .values("testresults__BatchID__BatchNo") \
                .annotate(ParticipantCount=Count("ParticipantID", distinct=True))  \
                .order_by("testresults__BatchID__BatchNo")


    response = {
        "level1": {
            "invite_count_lvl1": list(invite_count_results_level1),
            "passed_count_lvl1": list(passed_count_results_level1),
            "failed_count_lvl1": list(failed_count_results_level1),
            "in_progress_count_lvl1": list(in_progress_count_results_level1)
        },
        "level2": {
            "invite_count_lvl2": list(invite_count_results_level2),
            "passed_count_lvl2": list(passed_count_results_level2),
            "failed_count_lvl2": list(failed_count_results_level2),
            "in_progress_count_lvl2": list(in_progress_count_results_level2)
        }
    }

    return Response(response)
 

def get_invite_count_results(level):
    # expected result of above query
    #     [{BatchID__BatchNo': 'Batch1', 'LevelID__LevelNo': 'Level1', 'InviteCount': 10},
    #     {'BatchID__BatchNo': 'Batch2', 'LevelID__LevelNo': 'Level1', 'InviteCount': 15},
    # ]

    result = TestResult.objects.filter(LevelID__LevelNo=level) \
                    .values("BatchID__BatchNo", "LevelID__LevelNo") \
                    .annotate(InviteCount=Count("ParticipantID", distinct=True)) \
                    .order_by("BatchID__BatchNo", "LevelID__LevelNo")
    return result

