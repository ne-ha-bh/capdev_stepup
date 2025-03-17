from datetime import datetime
from django.utils.timezone import make_aware
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
import pandas as pd
import re
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from .models import Participant, Batch, Level, Subject, TestResult, UploadedFile, User, Role
from django.utils.timezone import now
from django.db.models import Count, Q
from django.http import FileResponse
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Prefetch
from django.http import JsonResponse


@api_view(['GET'])
def get_latest_uploads(request):
    latest_files = UploadedFile.objects.order_by('-upload_time')[:3]
    data = [{
        'file_name': f.file_name,
        'upload_time': f.upload_time.strftime("%d-%b-%Y, %I.%M %p %Z"),
        'file_id': f.id
    } for f in latest_files]
    return Response(data)
def convert_to_datetime(date_str):
    naive_datetime = datetime.strptime(date_str, '%A, %b %d %Y at %I:%M %p')
    return make_aware(naive_datetime)

def extract_attempt_no(test_name):
    match = re.search(r'Attempt([1-3])(?:\s|$)', test_name)
    if match:
        attempt_no_str = match.group(1)
        attempt_no = int(attempt_no_str)
        print(f"Extracted attempt_no: {attempt_no} from test_name: {test_name}")
        return attempt_no
    else:
        print(f"Extracted attempt_no: None from test_name: {test_name}")
        return None
    
def extract_batch_and_level(test_name):
    batch_match = re.search(r'Batch(\d+)', test_name)
    level_match = re.search(r'Level(\d+)', test_name)
    batch_no = f"Batch{batch_match.group(1)}" if batch_match else None
    level_no = f"L{level_match.group(1)}" if level_match else None
    return batch_no, level_no
@api_view(['GET'])
def download_file(request, file_id):
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id)
        return FileResponse(uploaded_file.file, as_attachment=True, filename=uploaded_file.file_name)
    except UploadedFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=404)
@api_view(['POST'])
def upload_data(request):
    file = request.FILES['file']
    print(f"Uploaded file: {file}")
    sheet_name = "List of Engineers Invited"
    df = pd.read_excel(file, sheet_name=sheet_name)
    print(f"Reading sheet: {sheet_name}")
    df.columns = df.columns.str.strip()
    UploadedFile.objects.create(file=file, file_name=file.name) 
    print(f"Columns in the uploaded file: {df.columns}")
    for index, row in df.iterrows():
        print(f"Processing row: {row}")
        name = row['Name']
        email = row['Email']
        primary_skill = row['Primary Skill'] if 'Primary Skill' in df.columns else None
        secondary_skill = row['Secondry Skill'] if 'Secondry Skill' in df.columns else None
        comments = row['comments'] if 'comments' in df.columns else None
        du = row['Delivery unit'] if 'Delivery unit' in df.columns else None
        designation = row['Designation'] if 'Designation' in df.columns else None
        emp_id = row['EmployeeId'] if 'EmployeeId' in df.columns else None
        invited_for_next_lvl = (
            True if row['Invitation sent for next level'].strip().lower() == 'yes' 
            else False if row['Invitation sent for next level'].strip().lower() == 'no' 
            else None
        ) if 'Invitation sent for next level' in df.columns and pd.notna(row['Invitation sent for next level']) else None
        is_active = (
            True if row['is_active'].strip().lower() == 'yes' 
            else False if row['is_active'].strip().lower() == 'no' 
            else None
        ) if 'Invitation sent for next level' in df.columns and pd.notna(row['Invitation sent for next level']) else None
        is_delete = row['is_delete'] if 'is_delete' in df.columns else None
        latest_level_passed = row['Latest level passed'] if 'Latest level passed' in df.columns else None
        involvement = row['Involvement'] if 'Involvement' in df.columns else None
        project_name = row['ProjectName'] if 'ProjectName' in df.columns else None
        role = row['Role'] if 'Role' in df.columns else None
        skills = row['Skills'] if 'Skills' in df.columns else None
        stepup_started = convert_to_datetime(row['StepUp_started_on']) if 'StepUp_started_on' in df.columns and pd.notna(row['StepUp_started_on']) else None
        total_exp = row['TotalExperience'] if 'TotalExperience' in df.columns else None
        subject_name =row['Subject name']
        test_name = row['Test name']
        no_of_attempts_invited = row['No of attempts invited'] if 'No of attempts invited' in df.columns and pd.notna(row['No of attempts invited']) else 0  # Default to 1 if NaN
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
        batch_no, level_no = extract_batch_and_level(test_name)
        print(f"batch_no: {batch_no}, level_no: {level_no}, attempt_no: {attempt_no}")

        with transaction.atomic():
            # Check if participant exists, if yes, update; if not, create
            if batch_no:
                batch, _ = Batch.objects.get_or_create(batch_no=batch_no)
            else:
                batch = None
            print(f"Batch processed: {batch}")
            level, _ = Level.objects.get_or_create(level_no=level_no)
            participant, created = Participant.objects.get_or_create(email=email)
            if created:
                print(f"Adding new participant to the database: {email}")
            else:
                print(f"Updating existing participant in the database: {email}")
            participant.name = name
            participant.primary_skill = primary_skill
            participant.secondary_skill = secondary_skill
            participant.comments = comments
            participant.delivery_unit = du
            participant.designation = designation
            participant.emp_id = emp_id
            participant.invited_for_next_lvl = invited_for_next_lvl
            participant.is_active = is_active
            participant.is_delete = is_delete
            if pd.isna(latest_level_passed):
                latest_level_passed_obj = None
            else:
                latest_level_passed_obj, _ = Level.objects.get_or_create(level_no=latest_level_passed)
            participant.latest_level_passed = latest_level_passed_obj 
            participant.project_involvement = involvement
            participant.project_name = project_name
            participant.role = role
            participant.skill = skills 
            participant.stepup_started = stepup_started
            participant.total_exp = total_exp
            participant.batch = batch
            participant.save()
            print(f"Participant saved: {participant}")
            #level, _ = Level.objects.get_or_create(level_no=level_no)
                        # latest_level_passed, _ = Level.objects.get_or_create(level_no=latest_level_passed) if latest_level_passed else (None)
            subject, created = Subject.objects.get_or_create(
                subject_name=subject_name,  # Remove unnecessary spaces
                defaults={'level': level}  # Only assign level if a new subject is created
            )

            #subject, _ = Subject.objects.get_or_create(subject_name=subject_name, level=level)
            print(f"Subject processed: {subject}")
            print(f"Creating TestResult for participant: {participant}, batch: {batch}, subject: {subject}, level: {level}, attempt: {attempt_no}")
            print(f"invite_time: {invite_time}, test_status: {test_status}, submitted_date: {submitted_date}, cn_rating: {cn_rating}, appeared_in_test: {appeared_in_test}, submitted_reason: {submitted_reason}, test_name: {test_name}")
            TestResult.objects.create(
                participant=participant,
                batch=batch,
                subject=subject,
                level=level,
                attempt=attempt_no,
                invite_time=invite_time,
                test_status=test_status,
                submitted_date=submitted_date,
                cn_rating=cn_rating,
                appeared_in_test=appeared_in_test,
                submitted_reason=submitted_reason, 
                no_of_attempts_invited = no_of_attempts_invited,
                test_name=test_name,
                created_date=now(),
                updated_date=now()
            )
            print(f"TestResult created for participant: {participant.email}")

    return Response({'message': 'Data uploaded successfully'}, status=200)

@api_view(['GET'])
def get_dashboard_data(request):
    # Aggregate data
    summary_data = Participant.objects.values('batch__batch_no', 'role').annotate(
        active_users=Count('participant_id', filter=Q(is_active=True)),
        l1=Count('participant_id', filter=Q(latest_level_passed__level_no='L1')),
        l2=Count('participant_id', filter=Q(latest_level_passed__level_no='L2')),
        l3=Count('participant_id', filter=Q(latest_level_passed__level_no='L3')),
        l4=Count('participant_id', filter=Q(latest_level_passed__level_no='L4')),
        l5=Count('participant_id', filter=Q(latest_level_passed__level_no='L5'))
    ).order_by('batch__batch_no', 'role')

    # Convert the data to a list of dictionaries
    summary_list = []
    for data in summary_data:
        summary_list.append({
            "Batch": data['batch__batch_no'],
            "Role": data['role'],
            "Active Users": data['active_users'],
            "L1": data['l1'],
            "L2": data['l2'],
            "L3": data['l3'],
            "L4": data['l4'],
            "L5": data['l5']
        })
    
    return Response(summary_list, status=200)

@api_view(['GET'])
def batch_role_summary(request):
    batch_no = request.GET.get('batch')
    role = request.GET.get('role')

    if not batch_no or not role:
        return Response({'error': 'Please provide both batch and role parameters'}, status=400)

    try:
        batch = Batch.objects.get(batch_no=batch_no)
    except Batch.DoesNotExist:
        return Response({'error': 'Batch not found'}, status=404)

    participants = Participant.objects.filter(batch=batch, role=role)

    if not participants.exists():
        return Response({'error': 'No participants found for the specified batch and role'}, status=404)

    batch_data = {
        'BatchNo': batch_no,
        'Roles': []
    }

    levels = ['L1', 'L2', 'L3', 'L4', 'L5']
    levels_data = []

    for level_no in levels:
        try:
            level = Level.objects.get(level_no=level_no)
        except Level.DoesNotExist:
            continue  # Skip if level is not found
        rolled_out_count = TestResult.objects.filter(
        batch=batch,
        participant__role=role,
        level=level
         ).values('participant').distinct().count()

        pass_count = TestResult.objects.filter(
        batch=batch,
        participant__role=role,
        level=level,
        test_status='pass'
        ).values('participant').distinct().count()

        fail_count = TestResult.objects.filter(
        batch=batch,
        participant__role=role,
        level=level,
        test_status='fail'
        ).values('participant').distinct().count()

        in_progress_count = TestResult.objects.filter(
        batch=batch,
        participant__role=role,
        level=level,
        test_status='in-progress'
        ).values('participant').distinct().count()
        yet_to_invite_count = participants.filter(
        batch=batch,
        role=role,
        latest_level_passed=level, 
        invited_for_next_lvl=True  
    ).count()
        levels_data.append({
            'Level': level_no,
            'Rolled_Out': rolled_out_count,
            'Pass': pass_count,
            'Fail': fail_count,
            'In_progress': in_progress_count,
            'Yet_to_invite_for_next_level': yet_to_invite_count
        })

    batch_data['Roles'].append({
        'Role': role,
        'Levels': levels_data
    })

    return Response({'batch_summary': batch_data})

@api_view(['GET'])
def get_batches(request):
    batches = Batch.objects.all().values('batch_id', 'batch_no')
    return Response(batches)

@api_view(['GET'])
def get_levels(request):
    levels = Level.objects.all().values('level_id', 'level_no')
    return Response(levels)

@api_view(['GET'])
def get_statuses(request):
    statuses = TestResult.objects.values_list('test_status', flat=True).distinct()
    return Response(list(statuses))

@api_view(['GET'])
def learner_detail(request):
    batch_id = request.GET.get('batch')
    level_id = request.GET.get('level')
    status = request.GET.get('status')
    print(f"Received request: batch={batch_id}, level={level_id}, status={status}")

    if not batch_id or not level_id or not status:
        return Response({'error': 'Please provide batch, level, and status parameters'}, status=400)

    try:
        batch = Batch.objects.get(batch_id=batch_id)
        level = Level.objects.get(level_id=level_id)
    except (Batch.DoesNotExist, Level.DoesNotExist):
        return Response({'error': 'Batch or level not found'}, status=404)

    test_results = TestResult.objects.filter(batch=batch, level=level)
    print(f"test_results count: {test_results.count()}")

    if status == 'pass':
        test_results = test_results.filter(test_status='pass')
    elif status == 'fail':
        test_results = test_results.filter(test_status='fail')
    else:
        test_results = test_results.filter(test_status='in-progress')

    learners_data = []

    if status == 'fail' and level.level_no == 'L1':
        # for failed L1 participants, including in-progress
        l1_subjects = Subject.objects.filter(level=level)
        print(f"L1 subjects count: {l1_subjects.count()}")
        print(f"L1 subjects: {[subject.subject_name for subject in l1_subjects]}")
        subject_names = [subject.subject_name for subject in l1_subjects]

        # Filter to include both 'fail' and 'in_progress'
        test_results = TestResult.objects.filter(batch=batch, level=level, test_status__in=['fail', 'in-progress'])

        for result in test_results:
            participant = result.participant
            subject_results = {}
            passed_count = 0

            for subject_name in subject_names:
                subject_result = TestResult.objects.filter(
                    participant=participant, batch=batch, level=level,
                    subject__subject_name=subject_name
                ).first()
                subject_results[subject_name] = subject_result.test_status if subject_result else 'Not Taken'
                if subject_result and subject_result.test_status == 'pass':
                    passed_count += 1

            learner_data = {
                'Name': participant.name,
                'Email ID': participant.email,
                'Level 1 Status': 'fail', 
                'No. of assessments Passed': passed_count,
            }
            learner_data.update(subject_results)
            learners_data.append(learner_data)
    elif status in ['fail', 'in-progress'] and level.level_no in ['L2', 'L3', 'L4', 'L5']:
        # Special format for L2, L3, L4, L5 failed/in-progress
        test_results = TestResult.objects.filter(batch=batch, level=level, test_status__in=['fail', 'in-progress'])

        for result in test_results:
            participant = result.participant
            learner_data = {
                'Name': participant.name,
                'Email ID': participant.email,
                f'Level {level.level_no[-1]} Status': result.test_status.capitalize(),
                'Primary Tech Stack': participant.primary_skill,
                'No. of attemps invited': result.no_of_attempts_invited,
                'No of times attempted': result.attempt or 0, #use 0 if attempt is null
            }
            learners_data.append(learner_data)
    else:
        # Standard format for other cases
        for result in test_results:
            participant = result.participant
            learners_data.append({
                'Name': participant.name,
                'Email ID': participant.email,
                'Primary Tech Stack': participant.primary_skill,
                'Invited for next level': 'Yes' if participant.invited_for_next_lvl else 'No'
            })

    return Response({
        'batch': batch.batch_no,
        'level': level.level_no,
        'status': status,
        'learners': learners_data
    })

@api_view(['POST'])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        if check_password(password, user.password): 
            refresh = RefreshToken.for_user(user)
            return Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'role': user.role.name,
                'email': user.email 
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

# @api_view(['GET'])
# def participant_data(request):
#     email = request.GET.get('email')
#     if not email:
#         return Response({'error': 'email is required'}, status=400)

#     try:
#         participant = Participant.objects.prefetch_related(
#             Prefetch('testresult_set', queryset=TestResult.objects.select_related('level', 'subject'))
#         ).get(email=email)

#         levels = Level.objects.order_by('-level_no')

#         result = {
#             'Name of the learner': participant.name,
#             'StepUp started on': participant.stepup_started.strftime('%d-%b-%Y-%I:%M %p %Z') if participant.stepup_started else None,
#             'Designation': participant.designation,
#             'Email ID': participant.email,
#             'Batch No': participant.batch.batch_no if participant.batch else None,
#             'Role': participant.role,
#         }

#         for level in levels:
#             level_data = {
#                 'Primary Tech Stack': [],
#                 'Status': [],
#                 'No of invites': [],
#                 'Last invited on': [],
#             }

#             test_results = [
#                 tr for tr in participant.testresult_set.all()
#                 if tr.level_id == level.level_id
#             ]

#             if not test_results:
#                  if level.level_no == 1:
#                     result[f'Level {level.level_no}'] = level_data
#                  else:
#                     result[f'Level {level.level_no}'] = level_data
#                  continue

#             for tr in test_results:
#                 level_data['Primary Tech Stack'].append(tr.subject.subject_name)
#                 level_data['Status'].append(tr.test_status)
#                 level_data['No of invites'].append(tr.no_of_attempts_invited)
#                 level_data['Last invited on'].append(tr.invite_time.strftime('%d-%b-%Y-%I:%M %p %Z'))

#             result[f'Level {level.level_no}'] = level_data
#         return Response(result)
#     except Participant.DoesNotExist:
#         return Response({'error': 'Participant not found'}, status=404)


@api_view(['GET'])
def participant_data(request):
    email = request.GET.get('email')
    name = request.GET.get('name')

    if not email and not name:
        return Response({'error': 'Either email or name is required'}, status=400)

    try:
        # Search by email or name
        if email:
            participant = Participant.objects.prefetch_related(
                Prefetch('testresult_set', queryset=TestResult.objects.select_related('level', 'subject'))
            ).get(email=email)
        else:
            participant = Participant.objects.prefetch_related(
                Prefetch('testresult_set', queryset=TestResult.objects.select_related('level', 'subject'))
            ).get(name=name)

        levels = Level.objects.order_by('-level_no')

        result = {
            'Name of the learner': participant.name,
            'StepUp started on': participant.stepup_started.strftime('%d-%b-%Y-%I:%M %p %Z') if participant.stepup_started else None,
            'Designation': participant.designation,
            'Email ID': participant.email,
            'Batch No': participant.batch.batch_no if participant.batch else None,
            'Role': participant.role,
        }

        for level in levels:
            level_data = {
                'Primary Tech Stack': [],
                'Status': [],
                'No of invites': [],
                'Last invited on': [],
            }

            test_results = [
                tr for tr in participant.testresult_set.all()
                if tr.level_id == level.level_id
            ]

            if not test_results:
                result[f'Level {level.level_no}'] = level_data
                continue

            for tr in test_results:
                level_data['Primary Tech Stack'].append(tr.subject.subject_name)
                level_data['Status'].append(tr.test_status)
                level_data['No of invites'].append(tr.no_of_attempts_invited)
                level_data['Last invited on'].append(tr.invite_time.strftime('%d-%b-%Y-%I:%M %p %Z'))

            result[f'Level {level.level_no}'] = level_data

        return Response(result)

    except Participant.DoesNotExist:
        return Response({'error': 'Participant not found'}, status=404)


@api_view(['POST'])
def send_query(request):
    email = request.data.get('email')
    comments = request.data.get('comments')
    print(f"email: {email}")
    print(f"comments: {comments}")
    if not email or not comments:
        return Response({'error': 'email and comments are required'}, status=400)

    try:
        participant = Participant.objects.get(email=email)
        subject = f"Comments for Participant: {participant.name}"
        message = f"Comments: {comments}\n\nParticipant ID: {participant.participant_id}\nName: {participant.name}\nEmail: {participant.email}"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = ['neha.bharti@harbingergroup.com']

        send_mail(subject, message, from_email, recipient_list)
        return Response({'message': 'Comments sent successfully'})
    
    except Participant.DoesNotExist:
        return Response({'error': 'Participant not found'}, status=404)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'error': f'Failed to send email: {str(e)}'}, status=500)

@api_view(['POST'])
def manage_participants(request):
    action = request.data.get('action')
    participant_id = request.data.get('participant_id')
    name = request.data.get('name')
    email = request.data.get('email')
    batch_id = request.data.get('batch_id')
    level_id = request.data.get('level_id')
    primary_skill = request.data.get('primary_skill')
    secondary_skill = request.data.get('secondary_skill')
    role = request.data.get('role')
    stepup_started = request.data.get('stepup_started')
    delivery_unit = request.data.get('delivery_unit')
    project_name = request.data.get('project_name')
    emp_id = request.data.get('emp_id')
    total_exp = request.data.get('total_exp')
    skill = request.data.get('skill')
    designation = request.data.get('designation')
    project_involvement = request.data.get('project_involvement')
    invited_for_next_lvl = request.data.get('invited_for_next_lvl')
    is_active = request.data.get('is_active')
    is_delete = request.data.get('is_delete')
    if action == 'add':
        try:
            batch = Batch.objects.get(batch_id=batch_id) if batch_id else None
            level = Level.objects.get(level_id=level_id) if level_id else None
            Participant.objects.create(
                name=name,
                email=email,
                primary_skill=primary_skill,
                secondary_skill=secondary_skill,
                batch=batch,
                role=role,
                stepup_started=stepup_started,
                delivery_unit=delivery_unit,
                project_name=project_name,
                emp_id=emp_id,
                total_exp=total_exp,
                skill=skill,
                designation=designation,
                project_involvement=project_involvement,
                latest_level_passed=level,
                invited_for_next_lvl=invited_for_next_lvl,
                is_active=is_active,
                is_delete=is_delete,
                # access_role=access_role, 
            )
            return Response({'message': 'Participant added successfully'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    elif action == 'edit':
        try:
            participant = Participant.objects.get(participant_id=participant_id)
            batch = Batch.objects.get(batch_id=batch_id) if batch_id else None
            level = Level.objects.get(level_id=level_id) if level_id else None
            participant.name = name
            participant.email = email
            participant.primary_skill = primary_skill
            participant.secondary_skill = secondary_skill
            participant.batch = batch
            participant.role = role
            participant.stepup_started = stepup_started
            participant.delivery_unit = delivery_unit
            participant.project_name = project_name
            participant.emp_id = emp_id
            participant.total_exp = total_exp
            participant.skill = skill
            participant.designation = designation
            participant.project_involvement = project_involvement
            participant.latest_level_passed = level
            participant.invited_for_next_lvl = invited_for_next_lvl
            participant.is_active = is_active
            participant.is_delete = is_delete
            #participant.access_role = access_role
            participant.updated_date = now()
            participant.save()

            return Response({'message': 'Participant updated successfully'}, status=status.HTTP_200_OK)
        except Participant.DoesNotExist:
            return Response({'error': 'Participant not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    elif action == 'delete':
        try:
            participant = Participant.objects.get(participant_id=participant_id)
            participant.delete()
            return Response({'message': 'Participant deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Participant.DoesNotExist:
            return Response({'error': 'Participant not found'}, status=status.HTTP_404_NOT_FOUND)

    else:
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
def get_participants(request):
    try:
        participants = Participant.objects.all().select_related('batch', 'latest_level_passed')
        participant_list = []
        for participant in participants:
            participant_data = {
                'participant_id': participant.participant_id,
                'name': participant.name,
                'email': participant.email,
                'primary_skill': participant.primary_skill,
                'secondary_skill': participant.secondary_skill,
                'role': participant.role,
                'stepup_started': participant.stepup_started.isoformat() if participant.stepup_started else None,
                'delivery_unit': participant.delivery_unit,
                'project_name': participant.project_name,
                'emp_id': participant.emp_id,
                'total_exp': participant.total_exp,
                'skill': participant.skill,
                'designation': participant.designation,
                'project_involvement': participant.project_involvement,
                'invited_for_next_lvl': participant.invited_for_next_lvl,
                'is_active': participant.is_active,
                'is_delete': participant.is_delete,
                
                'batch': {
                    'batch_id': participant.batch.batch_id,
                    'batch_no': participant.batch.batch_no,
                    'created_date': participant.batch.created_date.isoformat(),
                    'updated_date': participant.batch.updated_date.isoformat(),
                } if participant.batch else None,
                'latest_level_passed': {
                    'level_id': participant.latest_level_passed.level_id,
                    'level_no': participant.latest_level_passed.level_no,
                    'created_date': participant.latest_level_passed.created_date.isoformat(),
                    'updated_date': participant.latest_level_passed.updated_date.isoformat(),
                } if participant.latest_level_passed else None,
            }
            participant_list.append(participant_data)
        return Response(participant_list, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_role(request):
    name = request.data.get('name')  # Retrieve role name from request
    if not name:
        return JsonResponse({'error': 'Role name is required'}, status=400)

    # Check if role already exists
    if Role.objects.filter(name=name).exists():
        return JsonResponse({'error': 'Role already exists'}, status=400)

    # Create and save the role
    role = Role(name=name)
    role.save()

    return JsonResponse({'message': 'Role created successfully', 'data': {'id': role.id, 'name': role.name}}, status=201)
@api_view(['GET'])
def get_roles(request):
    roles = Role.objects.all().values('id', 'name')  # Query roles as dictionaries
    return JsonResponse({'data': list(roles)}, status=200)

@api_view(['POST'])
def create_user(request):
    name = request.data.get('name')
    email = request.data.get('email')
    password = request.data.get('password')
    role_id = request.data.get('role')

    # Validate input
    if not all([name, email, password, role_id]):
        return JsonResponse({'error': 'All fields (name, email, password, role) are required'}, status=400)

    # Validate role
    try:
        role = Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return JsonResponse({'error': 'Invalid role ID'}, status=400)

    # Check if email already exists
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Email already exists'}, status=400)

    # Hash the password and create the user
    hashed_password = make_password(password)
    user = User(name=name, email=email, password=hashed_password, role=role)
    user.save()

    return JsonResponse({
        'message': 'User created successfully',
        'data': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': {'id': role.id, 'name': role.name}
        }
    }, status=201)
@api_view(['GET'])
def get_users(request):
    users = User.objects.select_related('role').all()  # Fetch users with their roles
    user_data = [
        {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': {'id': user.role.id, 'name': user.role.name},
            'created_date': user.created_date,
            'updated_date': user.updated_date
        } for user in users
    ]
    return JsonResponse({'data': user_data}, status=200)
