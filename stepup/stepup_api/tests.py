from django.urls import reverse
import pandas as pd
from unittest.mock import patch, Mock
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Participant, Batch, Level, Subject, TestResult, UploadedFile, User, Role
import json
from django.core.files.uploadedfile import SimpleUploadedFile
from .views import get_users, extract_attempt_no, extract_batch_and_level,convert_to_datetime
from django.conf import settings
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password, make_password
from django.http import FileResponse
from django.utils.timezone import now
from datetime import datetime, timedelta
import os
import io

User = get_user_model()
class DownloadFileViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.test_file_name = 'test_file.txt'
        self.test_file_content = b'This is a test file.'
        self.test_file = SimpleUploadedFile(self.test_file_name, self.test_file_content)
        self.uploaded_file = UploadedFile.objects.create(file=self.test_file, file_name=self.test_file_name)

    def tearDown(self):
        file_path = os.path.join(settings.MEDIA_ROOT, self.uploaded_file.file.name)
        if os.path.exists(file_path):
            os.remove(file_path)

    def test_download_file_success(self):
        url = reverse('download_file', kwargs={'file_id': self.uploaded_file.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="{self.test_file_name}"')

        # Compare streaming content
        response_content = b''.join(response.streaming_content)
        self.assertEqual(response_content, self.test_file_content)

    def test_download_file_not_found(self):
        url = reverse('download_file', kwargs={'file_id': 999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'File not found'})
class GetRolesViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.role1 = Role.objects.create(name='learner')
        self.role2 = Role.objects.create(name='capdev')

    def test_get_roles_success(self):
        url = reverse('get_roles')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Sort the roles in the response by id
        data['data'] = sorted(data['data'], key=lambda x: x['id'])

        expected_data = {
            'data': [
                {'id': self.role1.id, 'name': self.role1.name},
                {'id': self.role2.id, 'name': self.role2.name},
            ]
        }
        self.assertEqual(data, expected_data)

    def test_get_roles_empty(self):
        Role.objects.all().delete()
        url = reverse('get_roles')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, {'data': []})

class GetLatestUploadsViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()  # Use APIClient for DRF views

        # Create some UploadedFile objects with different upload times
        now = timezone.now()
        UploadedFile.objects.create(file_name='file1.txt', upload_time=now - timedelta(days=3))
        UploadedFile.objects.create(file_name='file2.csv', upload_time=now - timedelta(days=1))
        UploadedFile.objects.create(file_name='file3.pdf', upload_time=now)
        UploadedFile.objects.create(file_name='file4.zip', upload_time=now - timedelta(days=2))
        UploadedFile.objects.create(file_name='file5.docx', upload_time=now - timedelta(days=4))

    def test_get_latest_uploads_success(self):
        url = reverse('get_latest_uploads')  # Make sure 'get_latest_uploads' matches your URL name
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data  # Access response data directly

        # Get the latest 3 files from the database and format their upload times
        latest_files = UploadedFile.objects.order_by('-upload_time')[:3]
        expected_data = [{
            'file_name': f.file_name,
            'upload_time': f.upload_time.strftime("%d-%b-%Y, %I.%M %p %Z"),
            'file_id': f.id
        } for f in latest_files]

        self.assertEqual(data, expected_data)

    def test_get_latest_uploads_empty(self):
        # Delete all files to test an empty response
        UploadedFile.objects.all().delete()
        url = reverse('get_latest_uploads')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

class UploadDataViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('upload_data')
        self.test_file_name = 'test_upload.xlsx'
        self.test_file_content = b'Name,Email,Test name,Invites Time,Appeared in test,Test Status,Submitted Date,Submitted reason,CN rating,Primary Skill,No of attempts invited,Invitation sent for next level,Role,Subject name,Delivery unit,Latest level passed,is_active,StepUp_started_on\nJino Thomas,Jino.Thomas@harbingergroup.com,Batch1_Level1_Intermediate StepUp_Prompt Engineering_Attempt2,"Thursday, Dec 26 2024 at 6:22 PM",Yes,pass,"Friday, Dec 27 2024 at 4:24 PM",User Submitted,5,python,1,Yes,Lead,Core Software Engineering Coding Skills,2,L1,Yes,'
        self.test_file = SimpleUploadedFile(self.test_file_name, self.test_file_content)

    def tearDown(self):
        for uploaded_file in UploadedFile.objects.all():
            file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.file.name)
            if os.path.exists(file_path):
                os.remove(file_path)

    @patch('pandas.read_excel')
    def test_upload_data_success(self, mock_read_excel):
        mock_read_excel.return_value = pd.read_csv(io.StringIO(self.test_file_content.decode('utf-8')))
        response = self.client.post(self.url, {'file': self.test_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'message': 'Data uploaded successfully'})

    # def test_upload_data_no_file(self):
    #     empty_file = SimpleUploadedFile('empty.xlsx', b'')  # Create an empty file
    #     response = self.client.post(self.url, {'file': empty_file}, format='multipart')
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(response.data['error'], "Uploaded file is empty")
    @patch('pandas.read_excel')
    def test_upload_data_invalid_data(self, mock_read_excel):
        invalid_content = b'Name,Email,Primary Skill,Subject name,Test name,Invites Time,Submitted Date,CN rating,Latest level passed\nInvalid Name,invalid_email,Test Subject,Subject,Test Batch1 Level2,"Thursday, Dec 26 2024 at 6:22 PM","Friday, Dec 27 2024 at 4:24 PM",5,L1\n'
        invalid_file = SimpleUploadedFile('invalid.xlsx', invalid_content)
        mock_read_excel.return_value = pd.read_csv(io.StringIO(invalid_content.decode('utf-8')))

        response = self.client.post(self.url, {'file': invalid_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
class GetDashboardDataViewTest(TestCase):


    def setUp(self):
        self.client = APIClient()
        self.url = '/dashboard'

        self.batch1 = Batch.objects.create(batch_no='Batch1')
        self.batch2 = Batch.objects.create(batch_no='Batch2')

        self.level1 = Level.objects.create(level_no='L1')
        self.level2 = Level.objects.create(level_no='L2')
        self.level3 = Level.objects.create(level_no='L3')
        self.level4 = Level.objects.create(level_no='L4')
        self.level5 = Level.objects.create(level_no='L5')

        # Corrected Participant creation
        Participant.objects.create(batch=self.batch1, role='Engineer', is_active=True, latest_level_passed=self.level1, email='etest1@example.com')
        Participant.objects.create(batch=self.batch1, role='Engineer', is_active=True, latest_level_passed=self.level1, email='engsampleeer2@example.com')
        Participant.objects.create(batch=self.batch1, role='Engineer', is_active=True, latest_level_passed=self.level2, email='engsampleeer3@example.com')
        Participant.objects.create(batch=self.batch1, role='Lead', is_active=True, latest_level_passed=self.level1, email='manaaaager1@example.com')
        Participant.objects.create(batch=self.batch1, role='Lead', is_active=True, latest_level_passed=self.level1, email='manaaaager2@example.com')

        Participant.objects.create(batch=self.batch2, role='Lead', is_active=True, latest_level_passed=self.level2, email='manageghjghgr2@example.com')
        Participant.objects.create(batch=self.batch2, role='Lead', is_active=True, latest_level_passed=self.level2, email='manageghjghgr3@example.com')
        Participant.objects.create(batch=self.batch2, role='Lead', is_active=True, latest_level_passed=self.level3, email='manageghjghgr4@example.com')
        Participant.objects.create(batch=self.batch2, role='Lead', is_active=True, latest_level_passed=self.level5, email='manageghjghgr5@example.com')
        Participant.objects.create(batch=self.batch2, role='Lead', is_active=True, latest_level_passed=self.level5, email='manageghjghgr6@example.com')

    def test_get_dashboard_data_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [
            {
                "Batch": "Batch1",
                "Role": "Engineer",
                "Active Users": 3,
                "L1": 2,
                "L2": 1,
                "L3": 0,
                "L4": 0,
                "L5": 0
            },
            {
                "Batch": "Batch1",
                "Role": "Lead",
                "Active Users": 2,
                "L1": 2,
                "L2": 0,
                "L3": 0,
                "L4": 0,
                "L5": 0
            },
            {
                "Batch": "Batch2",
                "Role": "Lead",
                "Active Users": 5,
                "L1": 0,
                "L2": 2,
                "L3": 1,
                "L4": 0,
                "L5": 2
            },
        ]
        self.assertEqual(response.data, expected_data)
    
    def test_get_dashboard_data_empty(self):
        Participant.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, []) 
    def test_get_dashboard_data_no_batches(self):
        Participant.objects.all().delete()
        Batch.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_dashboard_data_no_levels(self):
        Participant.objects.all().delete()
        Level.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
    def test_get_dashboard_data_invalid_url(self):
        response = self.client.get("/wrongurl/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
class BatchRoleSummaryViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/batch_role'  # Replace with your actual URL

        # Create test data
        self.batch1 = Batch.objects.create(batch_no='Batch1')
        self.batch2 = Batch.objects.create(batch_no='Batch2')

        self.level1 = Level.objects.create(level_no='L1')
        self.level2 = Level.objects.create(level_no='L2')
        self.level3 = Level.objects.create(level_no='L3')
        self.level4 = Level.objects.create(level_no='L4')
        self.level5 = Level.objects.create(level_no='L5')

        self.participant1 = Participant.objects.create(batch=self.batch1, role='Engineer', email='eng1@example.com', latest_level_passed=self.level1, invited_for_next_lvl=True)
        self.participant2 = Participant.objects.create(batch=self.batch1, role='Engineer', email='eng2@example.com', latest_level_passed=self.level2, invited_for_next_lvl=True)
        self.participant3 = Participant.objects.create(batch=self.batch1, role='Lead', email='lead1@example.com', latest_level_passed=self.level1, invited_for_next_lvl=False)
        self.participant4 = Participant.objects.create(batch=self.batch2, role='Engineer', email='eng3@example.com', latest_level_passed=self.level3, invited_for_next_lvl=False)

        #Create Subject objects.
        self.subject1 = Subject.objects.create(subject_name='Node')
        self.subject2 = Subject.objects.create(subject_name='React')
        TestResult.objects.create(participant=self.participant1, batch=self.batch1, level=self.level1, test_status='pass', subject=self.subject1, invite_time='2024-01-01T10:00:00')
        TestResult.objects.create(participant=self.participant1, batch=self.batch1, level=self.level2, test_status='fail', subject=self.subject2, invite_time='2024-01-02T10:00:00')
        TestResult.objects.create(participant=self.participant2, batch=self.batch1, level=self.level2, test_status='in-progress', subject=self.subject1, invite_time='2024-01-03T10:00:00')
        TestResult.objects.create(participant=self.participant3, batch=self.batch1, level=self.level1, test_status='pass', subject=self.subject2, invite_time='2024-01-04T10:00:00')
        TestResult.objects.create(participant=self.participant4, batch=self.batch2, level=self.level3, test_status='pass', subject=self.subject1, invite_time='2024-01-05T10:00:00')



    def test_batch_role_summary_success(self):
        response = self.client.get(self.url, {'batch': 'Batch1', 'role': 'Engineer'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            'batch_summary': {
                'BatchNo': 'Batch1',
                'Roles': [{
                    'Role': 'Engineer',
                    'Levels': [
                        {'Level': 'L1', 'Rolled_Out': 1, 'Pass': 1, 'Fail': 0, 'In_progress': 0, 'Yet_to_invite_for_next_level': 1},
                        {'Level': 'L2', 'Rolled_Out': 2, 'Pass': 0, 'Fail': 1, 'In_progress': 1, 'Yet_to_invite_for_next_level': 1},
                        {'Level': 'L3', 'Rolled_Out': 0, 'Pass': 0, 'Fail': 0, 'In_progress': 0, 'Yet_to_invite_for_next_level': 0},
                        {'Level': 'L4', 'Rolled_Out': 0, 'Pass': 0, 'Fail': 0, 'In_progress': 0, 'Yet_to_invite_for_next_level': 0},
                        {'Level': 'L5', 'Rolled_Out': 0, 'Pass': 0, 'Fail': 0, 'In_progress': 0, 'Yet_to_invite_for_next_level': 0},
                    ]
                }]
            }
        }
        self.assertEqual(response.data, expected_data)

    def test_batch_role_summary_invalid_batch(self):
        response = self.client.get(self.url, {'batch': 'InvalidBatch', 'role': 'Engineer'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'Batch not found'})

    def test_batch_role_summary_invalid_role(self):
        response = self.client.get(self.url, {'batch': 'Batch1', 'role': 'InvalidRole'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'No participants found for the specified batch and role'})

    def test_batch_role_summary_missing_parameters(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Please provide both batch and role parameters'})

    def test_batch_role_summary_empty_results(self):
        response = self.client.get(self.url, {'batch': 'Batch2', 'role': 'Lead'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'No participants found for the specified batch and role'})

    def test_batch_role_summary_no_test_results(self):
        participant5 = Participant.objects.create(batch=self.batch1, role='Engineer', email='eng5@example.com', latest_level_passed=self.level3)
        response = self.client.get(self.url, {'batch': 'Batch1', 'role': 'Engineer'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        #Check the rolled out counts are 0, and the rest match with the existing data.
        self.assertEqual(response.data['batch_summary']['Roles'][0]['Levels'][2]['Rolled_Out'], 0)
        self.assertEqual(response.data['batch_summary']['Roles'][0]['Levels'][2]['Pass'], 0)
        self.assertEqual(response.data['batch_summary']['Roles'][0]['Levels'][2]['Fail'], 0)
        self.assertEqual(response.data['batch_summary']['Roles'][0]['Levels'][2]['In_progress'], 0)
        self.assertEqual(response.data['batch_summary']['Roles'][0]['Levels'][2]['Yet_to_invite_for_next_level'], 0)


class GetBatchesViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/get_batches'  # Replace with your actual URL

        self.batch1 = Batch.objects.create(batch_no='Batch1')
        self.batch2 = Batch.objects.create(batch_no='Batch2')

    def test_get_batches_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_data = list(response.data)
        expected_data = [
            {'batch_id': self.batch1.batch_id, 'batch_no': 'Batch1'},
            {'batch_id': self.batch2.batch_id, 'batch_no': 'Batch2'},
        ]
        self.assertEqual(actual_data, expected_data)

    def test_get_batches_empty(self):
        Batch.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_data = list(response.data)
        self.assertEqual(actual_data, [])

class GetLevelsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/get_levels'  # Replace with your actual URL

        self.level1 = Level.objects.create(level_no='L1')
        self.level2 = Level.objects.create(level_no='L2')

    def test_get_levels_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_data = list(response.data)
        expected_data = [
            {'level_id': self.level1.level_id, 'level_no': 'L1'},
            {'level_id': self.level2.level_id, 'level_no': 'L2'},
        ]
        self.assertEqual(actual_data, expected_data)

    def test_get_levels_empty(self):
        Level.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_data = list(response.data)
        self.assertEqual(actual_data, [])

class GetStatusesViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/get_statuses'  
        self.batch = Batch.objects.create(batch_no='Batch1')
        self.level = Level.objects.create(level_no='L1')
        self.participant = Participant.objects.create(batch=self.batch, role='Engineer', email='test@example.com', latest_level_passed=self.level, invited_for_next_lvl=True)
        self.subject = Subject.objects.create(subject_name="Test")

        TestResult.objects.create(participant=self.participant, batch=self.batch, level=self.level, test_status='pass', subject=self.subject, invite_time='2024-01-01T10:00:00')
        TestResult.objects.create(participant=self.participant, batch=self.batch, level=self.level, test_status='fail', subject=self.subject, invite_time='2024-01-02T10:00:00')
        TestResult.objects.create(participant=self.participant, batch=self.batch, level=self.level, test_status='in-progress', subject=self.subject, invite_time='2024-01-03T10:00:00')

    def test_get_statuses_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_data = list(response.data)
        expected_data = ['pass', 'fail', 'in-progress']
        self.assertEqual(actual_data, expected_data)

    def test_get_statuses_empty(self):
        TestResult.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_data = list(response.data)
        self.assertEqual(actual_data, [])

class LearnerDetailViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/learner_detail'  # Replace with your actual URL

        self.batch1 = Batch.objects.create(batch_no='Batch1')
        self.batch2 = Batch.objects.create(batch_no='Batch2')

        self.level1 = Level.objects.create(level_no='L1')
        self.level2 = Level.objects.create(level_no='L2')
        self.level3 = Level.objects.create(level_no='L3')

        self.subject1 = Subject.objects.create(subject_name='Node', level=self.level1)
        self.subject2 = Subject.objects.create(subject_name='React', level=self.level1)
        self.subject3 = Subject.objects.create(subject_name='Python', level=self.level2)

        self.participant1 = Participant.objects.create(batch=self.batch1, name='Alice', email='alice@example.com', primary_skill='Python', latest_level_passed=self.level1, invited_for_next_lvl=True)
        self.participant2 = Participant.objects.create(batch=self.batch1, name='Bob', email='bob@example.com', primary_skill='Java', latest_level_passed=self.level2, invited_for_next_lvl=False)
        self.participant3 = Participant.objects.create(batch=self.batch2, name='Charlie', email='charlie@example.com', primary_skill='C++', latest_level_passed=self.level3, invited_for_next_lvl=False)

        self.test_result1 = TestResult.objects.create(participant=self.participant1, batch=self.batch1, level=self.level1, subject=self.subject1, test_status='pass', invite_time=timezone.now())
        self.test_result2 = TestResult.objects.create(participant=self.participant1, batch=self.batch1, level=self.level1, subject=self.subject2, test_status='fail', invite_time=timezone.now())
        self.test_result3 = TestResult.objects.create(participant=self.participant2, batch=self.batch1, level=self.level2, subject=self.subject3, test_status='fail', invite_time=timezone.now(), no_of_attempts_invited=2, attempt=1)
        self.test_result4 = TestResult.objects.create(participant=self.participant3, batch=self.batch2, level=self.level3, subject=self.subject3, test_status='in-progress', invite_time=timezone.now(), no_of_attempts_invited=3, attempt=2)

    def test_learner_detail_missing_params(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Please provide batch, level, and status parameters'})

    def test_learner_detail_batch_level_not_found(self):
        response = self.client.get(self.url, {'batch': 999, 'level': 999, 'status': 'pass'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'Batch or level not found'})

    def test_learner_detail_pass_l1(self):
        response = self.client.get(self.url, {'batch': self.batch1.batch_id, 'level': self.level1.level_id, 'status': 'pass'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['learners'], [{'Name': 'Alice', 'Email ID': 'alice@example.com', 'Primary Tech Stack': 'Python', 'Invited for next level': 'Yes'}])

    # def test_learner_detail_fail_l1(self):
    #     response = self.client.get(self.url, {'batch': self.batch1.batch_id, 'level': self.level1.level_id, 'status': 'fail'})
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     expected_result = [{'Name': 'Alice', 'Email ID': 'alice@example.com', 'Level 1 Status': 'fail', 'No. of assessments Passed': 1, 'Core Software Engineering': 'pass', 'Core Software Engineering Coding Skills': 'fail'}]
    #     self.assertCountEqual(response.data['learners'], expected_result)

    def test_learner_detail_fail_l2(self):
        response = self.client.get(self.url, {'batch': self.batch1.batch_id, 'level': self.level2.level_id, 'status': 'fail'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['learners'], [{'Name': 'Bob', 'Email ID': 'bob@example.com', 'Level 2 Status': 'Fail', 'Primary Tech Stack': 'Java', 'No. of attemps invited': 2, 'No of times attempted': 1}])

    def test_learner_detail_in_progress_l3(self):
        response = self.client.get(self.url, {'batch': self.batch2.batch_id, 'level': self.level3.level_id, 'status': 'in-progress'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class LoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/login'
        self.role = Role.objects.create(name='capdev')

        self.user = User.objects.create(
            email='test@example.com',
            password=make_password('testpassword'),
        )
        self.user.role = self.role 
        self.user.save()
    
    def test_login_missing_email(self):
        data = {'password': 'testpassword'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Email and password are required.'})

    def test_login_missing_password(self):
        data = {'email': 'test@example.com'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Email and password are required.'})


class ParticipantDataViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/participant_data/' 

        self.batch = Batch.objects.create(batch_no='Batch1')
        self.level1 = Level.objects.create(level_no='L1')
        self.level2 = Level.objects.create(level_no='L2')
        self.subject1 = Subject.objects.create(subject_name='Python', level=self.level1)
        self.subject2 = Subject.objects.create(subject_name='Java', level=self.level2)

        self.participant = Participant.objects.create(
            name='Test Participant',
            email='test@example.com',
            batch=self.batch,
            role='Developer',
            stepup_started=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            designation='Software Engineer'
        )

        self.test_result1 = TestResult.objects.create(
            participant=self.participant,
            batch=self.batch,
            level=self.level1,
            subject=self.subject1,
            test_status='pass',
            no_of_attempts_invited=2,
            invite_time=datetime(2023, 1, 5, 12, 0, tzinfo=timezone.utc)
        )

        self.test_result2 = TestResult.objects.create(
            participant=self.participant,
            batch=self.batch,
            level=self.level2,
            subject=self.subject2,
            test_status='fail',
            no_of_attempts_invited=3,
            invite_time=datetime(2023, 1, 10, 14, 0, tzinfo=timezone.utc)
        )

    def test_participant_data_by_email_success(self):
        response = self.client.get(self.url, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_result = {
            'Name of the learner': 'Test Participant',
            'StepUp started on': '01-Jan-2023-10:00 AM UTC',
            'Designation': 'Software Engineer',
            'Email ID': 'test@example.com',
            'Batch No': 'Batch1',
            'Role': 'Developer',
            'Level L2': {
                'Primary Tech Stack': ['Java'],
                'Status': ['fail'],
                'No of invites': [3],
                'Last invited on': ['10-Jan-2023-02:00 PM UTC']
            },
            'Level L1': {
                'Primary Tech Stack': ['Python'],
                'Status': ['pass'],
                'No of invites': [2],
                'Last invited on': ['05-Jan-2023-12:00 PM UTC']
            }
        }
        self.assertEqual(response.data, expected_result)

    def test_participant_data_by_name_success(self):
        response = self.client.get(self.url, {'name': 'Test Participant'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_result = {
            'Name of the learner': 'Test Participant',
            'StepUp started on': '01-Jan-2023-10:00 AM UTC',
            'Designation': 'Software Engineer',
            'Email ID': 'test@example.com',
            'Batch No': 'Batch1',
            'Role': 'Developer',
            'Level L2': {
                'Primary Tech Stack': ['Java'],
                'Status': ['fail'],
                'No of invites': [3],
                'Last invited on': ['10-Jan-2023-02:00 PM UTC']
            },
            'Level L1': {
                'Primary Tech Stack': ['Python'],
                'Status': ['pass'],
                'No of invites': [2],
                'Last invited on': ['05-Jan-2023-12:00 PM UTC']
            }
        }
        self.assertEqual(response.data, expected_result)

    def test_participant_data_missing_params(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Either email or name is required'})

    def test_participant_data_participant_not_found_email(self):
        response = self.client.get(self.url, {'email': 'nonexistent@example.com'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'Participant not found'})

    def test_participant_data_participant_not_found_name(self):
        response = self.client.get(self.url, {'name': 'Nonexistent Participant'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'Participant not found'})

    def test_participant_data_no_test_results(self):
        participant_no_results = Participant.objects.create(
            name='No Results',
            email='noresults@example.com',
            batch=self.batch,
            role='Tester'
        )
        response = self.client.get(self.url, {'email': 'noresults@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['Level L1'], {'Primary Tech Stack': [], 'Status': [], 'No of invites': [], 'Last invited on': []})
        self.assertEqual(response.data['Level L2'], {'Primary Tech Stack': [], 'Status': [], 'No of invites': [], 'Last invited on': []})


# from django.test import TestCase, override_settings

# @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
# class SendQueryViewTest(TestCase):
#     def setUp(self):
#         self.client = APIClient()
#         self.url = '/send-query'  # Replace with your actual URL
#         self.batch = Batch.objects.create(batch_no='Batch1')
#         self.role = Role.objects.create(name='capdev')
#         self.user = User.objects.create(
#             username='testuser',
#             email='test@example.com',
#             password=make_password('testpassword'),
#         )
#         self.user.role = self.role
#         self.user.save()

#         self.participant = Participant.objects.create(
#             name='Test Participant',
#             email='test@example.com',
#             batch=self.batch,
#             role='Developer'
#         )

#     def test_send_query_success(self):
#         data = {'email': 'test@example.com', 'comments': 'This is a test comment.'}
#         response = self.client.post(self.url, data)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data, {'message': 'Comments sent successfully'})
#         self.assertEqual(len(mail.outbox), 1)
#         self.assertEqual(mail.outbox[0].subject, f"Comments for Participant: {self.participant.name}")
#         self.assertIn(data['comments'], mail.outbox[0].body)
#         self.assertIn(str(self.participant.participant_id), mail.outbox[0].body)

#     def test_send_query_missing_email(self):
#         data = {'comments': 'This is a test comment.'}
#         response = self.client.post(self.url, data)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertEqual(response.data, {'error': 'email and comments are required'})

#     def test_send_query_missing_comments(self):
#         data = {'email': 'test@example.com'}
#         response = self.client.post(self.url, data)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertEqual(response.data, {'error': 'email and comments are required'})

#     def test_send_query_participant_not_found(self):
#         data = {'email': 'nonexistent@example.com', 'comments': 'This is a test comment.'}
#         response = self.client.post(self.url, data)
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#         self.assertEqual(response.data, {'error': 'Participant not found'})

#     def test_send_query_email_failure(self):
#         #Simulate an email failure
#         with self.assertRaises(Exception):
#             with override_settings(EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend'): #dummy email backend will not send mail.
#                 data = {'email': 'test@example.com', 'comments': 'This is a test comment.'}
#                 response = self.client.post(self.url, data)
#                 self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
#                 self.assertIn('Failed to send email', response.data['error'])

#     def test_send_query_missing_both(self):
#         response = self.client.post(self.url, {})
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertEqual(response.data, {'error': 'email and comments are required'})
class ManageParticipantsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/manage_participants"  # Replace with your actual URL
        self.batch = Batch.objects.create(batch_no='Batch1')
        self.level = Level.objects.create(level_no='L1')
        self.role = Role.objects.create(name="learner")

        self.participant = Participant.objects.create(
            name='Old Name',
            email='old@example.com',
            batch=self.batch,
            role="learner",
            latest_level_passed=self.level
        )

    def test_add_participant_success(self):
        data = {
            'action': 'add',
            'name': 'New Participant',
            'email': 'new@example.com',
            'batch_id': self.batch.batch_id,
            'level_id': self.level.level_id,
            'primary_skill': 'Python',
            'role' : "learner",
            'stepup_started' : datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            'is_active': True,
            'is_delete': False
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'message': 'Participant added successfully'})
        self.assertTrue(Participant.objects.filter(name='New Participant', email='new@example.com').exists())

    def test_add_participant_missing_required_data(self):
        data = {'action': 'add', 'name': 'New Participant'}  # Missing email
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edit_participant_success(self):
        data = {
            'action': 'edit',
            'participant_id': self.participant.participant_id,
            'name': 'Updated Name',
            'email': 'updated@example.com',
            'batch_id': self.batch.batch_id,
            'level_id': self.level.level_id,
            'role' : "learner",
            'stepup_started' : datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            'is_active': True,
            'is_delete': False
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'message': 'Participant updated successfully'})
        self.assertTrue(Participant.objects.filter(name='Updated Name', email='updated@example.com').exists())

    def test_edit_participant_not_found(self):
        data = {'action': 'edit', 'participant_id': 999}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'Participant not found'})

    def test_delete_participant_success(self):
        data = {'action': 'delete', 'participant_id': self.participant.participant_id}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Participant.objects.filter(participant_id=self.participant.participant_id).exists())

    def test_delete_participant_not_found(self):
        data = {'action': 'delete', 'participant_id': 999}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': 'Participant not found'})

    def test_invalid_action(self):
        data = {'action': 'invalid'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Invalid action'})


class GetParticipantsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/get_participants"  # Assuming your URL is /get_participants
        self.batch = Batch.objects.create(batch_no='Batch1')
        self.level = Level.objects.create(level_no='L1')
        self.role = Role.objects.create(name="learner")

        self.participant1 = Participant.objects.create(
            name='Participant 1',
            email='participant1@example.com',
            batch=self.batch,
            role="learner",
            latest_level_passed=self.level,
            stepup_started=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            is_active=True,
            is_delete=False
        )

        self.participant2 = Participant.objects.create(
            name='Participant 2',
            email='participant2@example.com',
            batch=self.batch,
            role="learner",
            latest_level_passed=self.level,
            stepup_started=datetime(2023, 1, 2, 11, 0, tzinfo=timezone.utc),
            is_active=True,
            is_delete=False
        )

    def test_get_participants_empty(self):
        Participant.objects.all().delete() #delete all participant
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_participants_internal_server_error(self):
        # Simulate an exception in the view
        def mock_all():
            raise Exception("Simulated error")

        Participant.objects.all = mock_all
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data, {'error': 'Simulated error'})
        #reset the mock
        Participant.objects.all = Participant.objects.all
class CreateRoleViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/create_role"

    def test_create_role_success(self):
        data = {'name': 'NewRole'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), {'message': 'Role created successfully', 'data': {'id': Role.objects.get(name='NewRole').id, 'name': 'NewRole'}})
        self.assertTrue(Role.objects.filter(name='NewRole').exists())

    def test_create_role_missing_name(self):
        data = {}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'error': 'Role name is required'})

    def test_create_role_already_exists(self):
        Role.objects.create(name='ExistingRole')
        data = {'name': 'ExistingRole'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'error': 'Role already exists'})
    def test_create_role_empty_name(self):
        data = {'name': ''}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'error': 'Role name is required'})

class GetRolesViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/get_roles"
        Role.objects.create(name='Role1')
        Role.objects.create(name='Role2')

    def test_get_roles_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {'data': [{'id': role.id, 'name': role.name} for role in Role.objects.all().order_by('id')]}
        self.assertEqual(response.json(), expected_data)


class CreateUserViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/create_user"
        self.role = Role.objects.create(name='TestRole')

    def test_create_user_missing_fields(self):
        data = {'name': 'TestUser', 'email': 'test@example.com'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'error': 'All fields (name, email, password, role) are required'})

    def test_create_user_invalid_role(self):
        data = {
            'name': 'TestUser',
            'email': 'test@example.com',
            'password': 'password123',
            'role': 999
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'error': 'Invalid role ID'})

class GetUsersViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/get_users"
        self.role = Role.objects.create(name='TestRole')
        self.user1 = User.objects.create(email='user1@example.com', password=make_password('password123'))
        self.user1.role = self.role
        self.user1.save()
        self.user2 = User.objects.create(email='user2@example.com', password=make_password('password123'))
        self.user2.role = self.role
        self.user2.save()