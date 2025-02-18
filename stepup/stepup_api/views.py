import re
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from .models import Participant, Batch, Level, Subject, Attempt, TestResult
import pandas as pd
from datetime import datetime
from django.db.models import Count, Max, Min, F, Q, Sum
from django.http import JsonResponse
from django.utils.timezone import make_aware
from django.db import connection
import logging

logger = logging.getLogger('django')
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

# def user_details(request):
#     email = request.GET.get('email')
#     if not email:
#         return JsonResponse({'error': 'Missing required parameters'}, status=400)

#     try:
#         participant = Participant.objects.get(email=email)
#     except Participant.DoesNotExist:
#         return JsonResponse({'message': 'User not found!'}, status=404)

#     level_details = {}

#     def get_level_details(level_no):
#         results = TestResult.objects.filter(
#             participant__email=email,
#             level__level_no=level_no
#         ).values(
#             'participant__name',
#             'participant__email',
#             'subject__subject_name',
#             'batch__batch_no'
#         ).annotate(
#             TotalInvites=Count('test_result_id'),
#             LastInviteDate=Max('invite_time'),
#             FirstInviteDate=Min('invite_time')
#         ).order_by('-LastInviteDate')

#         level_test_details = []
#         for result in results:
#             detail = {
#                 'ParticipantName': result['participant__name'],
#                 'Email': result['participant__email'],
#                 'SubjectName': result['subject__subject_name'],
#                 'BatchNo': result['batch__batch_no'],
#                 'TotalInvites': result['TotalInvites'],
#                 'LastInvited': result['LastInviteDate'],
#                 'StartDate': result['FirstInviteDate'],
#             }

#             passed_count = TestResult.objects.filter(
#                 participant__email=email,
#                 level__level_no=level_no,
#                 cn_rating__gte=4
#             ).count()

#             if passed_count:
#                 detail['TestStatus'] = 'Passed'
#                 detail['InviteForNextLevel'] = 'No'
#                 detail['InviteDate'] = None
#             else:
#                 detail['TestStatus'] = 'Failed'

#                 next_level_no = {
#                     'Level1': 'Level2',
#                     'Level2': 'Level3',
#                     'Level3': 'Level4',
#                     'Level4': 'Level5'
#                 }.get(level_no)

#                 next_level_invite_date = TestResult.objects.filter(
#                     participant__email=email,
#                     level__level_no=next_level_no
#                 ).aggregate(Min('invite_time'))['invite_time__min']

#                 if next_level_invite_date:
#                     detail['InviteForNextLevel'] = 'Yes'
#                     detail['InviteDate'] = next_level_invite_date
#                 else:
#                     detail['InviteForNextLevel'] = 'No'
#                     detail['InviteDate'] = None

#             level_test_details.append(detail)

#         return level_test_details

#     level_details['Level 1'] = get_level_details('Level 1')
#     level_details['Level 2'] = get_level_details('Level 2')

#     overall_status = 'Failed'
#     for level in level_details.values():
#         for detail in level:
#             if detail['TestStatus'] == 'Passed':
#                 overall_status = 'Passed'
#                 break
#     if level_details['Level 2']:
#         for detail in level_details['Level 1']:
#             detail['InviteForNextLevel'] = 'Yes'
#     return JsonResponse({
#         'participant': participant.name,
#         'test_status': overall_status,
#         'details': level_details
#     }, status=200)

from django.http import JsonResponse
from django.db.models import Count, Max, Min
from .models import Participant, TestResult

def user_details(request):
    email = request.GET.get('email')
    if not email:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)

    try:
        participant = Participant.objects.get(email=email)
    except Participant.DoesNotExist:
        return JsonResponse({'message': 'User not found!'}, status=404)

    level_details = {}

    def get_level_details(level_no):
        results = TestResult.objects.filter(
            participant__email=email,
            level__level_no=level_no
        ).values(
            'participant__name',
            'participant__email',
            'subject__subject_name',
            'batch__batch_no'
        ).annotate(
            TotalInvites=Count('test_result_id'),
            LastInviteDate=Max('invite_time'),
            FirstInviteDate=Min('invite_time')
        ).order_by('-LastInviteDate')

        level_test_details = []
        for result in results:
            detail = {
                'ParticipantName': result['participant__name'],
                'Email': result['participant__email'],
                'SubjectName': result['subject__subject_name'],
                'BatchNo': result['batch__batch_no'],
                'TotalInvites': result['TotalInvites'],
                'LastInvited': result['LastInviteDate'],
                'StartDate': result['FirstInviteDate'],
            }

            passed_count = TestResult.objects.filter(
                participant__email=email,
                level__level_no=level_no,
                cn_rating__gte=4
            ).count()

            if passed_count:
                detail['TestStatus'] = 'Passed'
                detail['InviteForNextLevel'] = 'No'
                detail['InviteDate'] = None
            else:
                detail['TestStatus'] = 'Failed'

                next_level_no = {
                    'Level1': 'Level2',
                    'Level2': 'Level3',
                    'Level3': 'Level4',
                    'Level4': 'Level5'
                }.get(level_no)

                next_level_invite_date = TestResult.objects.filter(
                    participant__email=email,
                    level__level_no=next_level_no
                ).aggregate(Min('invite_time'))['invite_time__min']

                if next_level_invite_date:
                    detail['InviteForNextLevel'] = 'Yes'
                    detail['InviteDate'] = next_level_invite_date
                else:
                    detail['InviteForNextLevel'] = 'No'
                    detail['InviteDate'] = None

            level_test_details.append(detail)

        return level_test_details

    # Fetch details in decreasing order of levels
    level_details['Level 2'] = get_level_details('Level2')
    level_details['Level 1'] = get_level_details('Level1')

    overall_status = 'Failed'
    for level in level_details.values():
        for detail in level:
            if detail['TestStatus'] == 'Passed':
                overall_status = 'Passed'
                break

    if level_details['Level 2']:
        for detail in level_details['Level 1']:
            detail['InviteForNextLevel'] = 'Yes'

    return JsonResponse({
        'participant': participant.name,
        'primary_skill': participant.primary_skill,
        'test_status': overall_status,
        'details': level_details
    }, status=200)

def get_participant_details(request):
    batch_no = request.GET.get('batch_id')
    level_id = request.GET.get('level_id')
    subject_name = request.GET.get('subject_name')
    attempt_no = request.GET.get('attempt_id')
    status = request.GET.get('status')
    if not batch_no or not level_id or not subject_name or not attempt_no or not status:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    try:
        batch = Batch.objects.get(batch_no=batch_no)
    except Batch.DoesNotExist:
        return JsonResponse({'error': 'Invalid batch_id'}, status=400)
    try:
        attempt = Attempt.objects.get(attempt_no=attempt_no)
    except Attempt.DoesNotExist:
        return JsonResponse({'error': 'Invalid attempt_id'}, status=400)
    status_filter = {}
    if status == 'pass':
        status_filter['cn_rating__gte'] = 4.0
    elif status == 'fail':
        status_filter['cn_rating__lt'] = 4.0
        status_filter['appeared_in_test'] = True
    elif status == 'total_appeared':
        status_filter['appeared_in_test'] = True

    results = TestResult.objects.filter(
        batch_id=batch.batch_id,
        level_id=level_id,
        subject_id__subject_name=subject_name,
        attempt_id=attempt.attempt_id,
        **status_filter
    ).values(
        'participant_id__name',
        'participant_id__email'
    )
    data = [{'Name': result['participant_id__name'], 'Email': result['participant_id__email']} for result in results]
    return JsonResponse(data, safe=False, status=200)

def get_candidates_in_progress(request):
    batch_no = request.GET.get('batch_no')
    level_no = request.GET.get('level_no')
    if not batch_no or not level_no:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    try:
        batch = Batch.objects.get(batch_no=batch_no)
    except Batch.DoesNotExist:
        return JsonResponse({'error': 'Invalid batch_no'}, status=400)
    try:
        level = Level.objects.get(level_no=level_no)
    except Level.DoesNotExist:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)
    next_level_no = ''
    if level_no == 'Level 1':
        next_level_no = 'Level 2'
    elif level_no == 'Level 2':
        next_level_no = 'Level 3'
    else:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)
    try:
        next_level = Level.objects.get(level_no=next_level_no)
        next_level_id = next_level.level_id
    except Level.DoesNotExist:
        next_level_id = None
    in_progress_candidates = Participant.objects.filter(
        Q(testresult__batch=batch) &
        Q(testresult__level=level) &
        Q(testresult__cn_rating__gte=0) &
        Q(testresult__cn_rating__lt=4.0) &
        ~Q(testresult__participant_id__in=TestResult.objects.filter(
            batch=batch, level=level, cn_rating__gte=4.0).values('participant_id'))
    ).distinct()
    candidates_data = []
    for candidate in in_progress_candidates:
        candidate_id = candidate.participant_id
        if next_level_id is None:
            is_invited = 'Not Invited'
        else:
            invited_count = TestResult.objects.filter(
                participant=candidate,
                batch=batch,
                level_id=next_level_id
            ).count()
            is_invited = 'Yes' if invited_count > 0 else 'No'
        candidate_data = {
            'Name': candidate.name,
            'Email': candidate.email,
            'PrimarySkill': candidate.primary_skill,
            'InvitedForNextLevel': is_invited
        }
        candidates_data.append(candidate_data)
    return JsonResponse({
        'InProgressCount': len(candidates_data),
        'InProgressCandidates': candidates_data
    }, status=200)

def get_fail_candidates(request):
    batch_no = request.GET.get('batch_no')
    level_no = request.GET.get('level_no')
    if not batch_no or not level_no:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    try:
        batch = Batch.objects.get(batch_no=batch_no)
    except Batch.DoesNotExist:
        return JsonResponse({'error': 'Invalid batch_no'}, status=400)
    try:
        level = Level.objects.get(level_no=level_no)
    except Level.DoesNotExist:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)
    next_level_no = ''
    if level_no == 'Level 1':
        next_level_no = 'Level 2'
    elif level_no == 'Level 2':
        next_level_no = 'Level 3'
    else:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)
    try:
        next_level = Level.objects.get(level_no=next_level_no)
        next_level_id = next_level.level_id
    except Level.DoesNotExist:
        next_level_id = None
    if level_no == 'Level 1':
        candidates_results = Participant.objects.filter(
            testresult__batch=batch,
            testresult__level=level,
            testresult__cn_rating__lt=4.0,
            testresult__attempt__attempt_no='Attempt 3'
        ).distinct()
        subjects_list = list(Subject.objects.values_list('subject_name', flat=True))
        logger.debug(f"Fetched Subjects: {subjects_list}")
        candidates_data = []
        for candidate in candidates_results:
            candidate_id = candidate.participant_id

            test_results = TestResult.objects.filter(
                batch=batch,
                level=level,
                participant=candidate,
                subject__subject_name__in=subjects_list
            ).values(
                'subject__subject_name',
                'cn_rating',
                'attempt__attempt_no',
                'invite_time',
                'appeared_in_test'
            )
            subject_status = {subject: 'fail' for subject in subjects_list}
            for row in test_results:
                subj = row['subject__subject_name']
                if row['cn_rating'] is not None and row['cn_rating'] >= 4.0:
                    subject_status[subj] = 'pass'

            agg_result = TestResult.objects.filter(
                batch=batch,
                level=level,
                participant=candidate
            ).aggregate(
                total_invitations=Count('test_result_id'),
                last_invited=Max('invite_time'),
                total_appeared=Sum('appeared_in_test')
            )
            if next_level_id is None:
                is_invited = 'Not Invited'
            else:
                invited_count = TestResult.objects.filter(
                    participant=candidate,
                    batch=batch,
                    level_id=next_level_id
                ).count()
                is_invited = 'Yes' if invited_count > 0 else 'No'
            candidate_data = {
                'Name': candidate.name,
                'Email': candidate.email,
                'PrimarySkill': candidate.primary_skill,
                'TotalInvitations': agg_result['total_invitations'],
                'LastInvited': agg_result['last_invited'],
                'TotalAppeared': agg_result['total_appeared'],
                'Subjects': [
                    {'SubjectName': subj, 'Status': subject_status[subj]}
                    for subj in subjects_list
                ],
                'InvitedForNextLevel': is_invited
            }
            candidates_data.append(candidate_data)
        return JsonResponse(candidates_data, safe=False, status=200)
    elif level_no == 'Level 2':
        candidates_results = Participant.objects.filter(
            testresult__batch=batch,
            testresult__level=level,
            testresult__cn_rating__lt=4.0,
            testresult__attempt__attempt_no='Attempt 3'
        ).distinct()
        subjects_list = list(Subject.objects.values_list('subject_name', flat=True))
        logger.debug(f"Fetched Subjects: {subjects_list}")
        candidates_data = []
        for candidate in candidates_results:
            candidate_id = candidate.participant_id
            test_results = TestResult.objects.filter(
                batch=batch,
                level=level,
                participant=candidate,
                subject__subject_name__in=subjects_list
            ).values(
                'subject__subject_name',
                'cn_rating',
                'attempt__attempt_no',
                'invite_time',
                'appeared_in_test'
            )
            subject_status = {subject: 'fail' for subject in subjects_list}
            for row in test_results:
                subj = row['subject__subject_name']
                if row['cn_rating'] is not None and row['cn_rating'] >= 4.0:
                    subject_status[subj] = 'pass'
            candidate_data = {
                'Name': candidate.name,
                'Email': candidate.email,
                'PrimarySkill': candidate.primary_skill,
                'Subjects': [
                    {'SubjectName': subj, 'Status': subject_status[subj]}
                    for subj in subjects_list
                ]
            }
            candidates_data.append(candidate_data)
        return JsonResponse(candidates_data, safe=False, status=200)
    else:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)

def get_pass_candidates(request):
    batch_no = request.GET.get('batch_no')
    level_no = request.GET.get('level_no')
    if not batch_no or not level_no:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    try:
        batch = Batch.objects.get(batch_no=batch_no)
    except Batch.DoesNotExist:
        return JsonResponse({'error': 'Invalid batch_no'}, status=400)
    try:
        level = Level.objects.get(level_no=level_no)
    except Level.DoesNotExist:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)
    next_level_no = ''
    if level_no == 'Level 1':
        next_level_no = 'Level 2'
    elif level_no == 'Level 2':
        next_level_no = 'Level 3'
    else:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)
    try:
        next_level = Level.objects.get(level_no=next_level_no)
        next_level_id = next_level.level_id
    except Level.DoesNotExist:
        next_level_id = None
    if level_no == 'Level 1':
        required_subjects = ['Core Software Engineering', 'Prompt Engineering', 'Core Software Engineering Coding Skills']
        subject_ids = list(Subject.objects.filter(subject_name__in=required_subjects).values_list('subject_id', flat=True))
        passed_candidates = Participant.objects.filter(
            Q(testresult__batch=batch) &
            Q(testresult__level=level) &
            Q(testresult__cn_rating__gt=4.0) &
            Q(participant_id__in=TestResult.objects.filter(
                level=level, cn_rating__gt=4.0, subject_id__in=subject_ids
            ).values('participant_id').annotate(
                subject_count=Count('subject', distinct=True)
            ).filter(
                subject_count=len(required_subjects)
            ).values('participant_id'))
        ).distinct()
    elif level_no == 'Level 2':
        passed_candidates = Participant.objects.filter(
            Q(testresult__batch=batch) &
            Q(testresult__level=level) &
            Q(testresult__cn_rating__gte=4.0)
        ).distinct()
    else:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)

    candidates_data = []
    for candidate in passed_candidates:
        name = candidate.name
        email = candidate.email
        primary_skill = candidate.primary_skill

        if next_level_id is None:
            is_invited = 'Not Invited'
        else:
            invited_count = TestResult.objects.filter(
                participant=candidate,
                batch=batch,
                level_id=next_level_id
            ).count()
            is_invited = 'Yes' if invited_count > 0 else 'No'

        candidates_data.append({
            'Name': name,
            'Email': email,
            'PrimarySkill': primary_skill,
            'InvitedForNextLevel': is_invited
        })
    return JsonResponse(candidates_data, safe=False, status=200)

def get_total_invites(request):
    batch_no = request.GET.get('batch_no')
    level_no = request.GET.get('level_no')
    if not batch_no or not level_no:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    try:
        batch = Batch.objects.get(batch_no=batch_no)
    except Batch.DoesNotExist:
        return JsonResponse({'error': 'Invalid batch_no'}, status=400)
    try:
        level = Level.objects.get(level_no=level_no)
    except Level.DoesNotExist:
        return JsonResponse({'error': 'Invalid level_no'}, status=400)
    results = Participant.objects.filter(
        testresult__batch=batch,
        testresult__level=level
    ).annotate(
        TotalInvites=Count('testresult__invite_time')
    ).values(
        'name', 'email', 'primary_skill', 'TotalInvites'
    )
    invited_candidates = []
    for row in results:
        invited_candidates.append({
            'Name': row['name'],
            'Email': row['email'],
            'TechStack': row['primary_skill'],
            'TotalInvites': row['TotalInvites']
        })
    return JsonResponse(invited_candidates, safe=False, status=200)
