from django.urls import path
from .views import upload_data, get_dashboard_data ,batch_role_summary, learner_detail, get_batches, get_levels, get_statuses ,download_file, get_latest_uploads, login, participant_data, send_query, manage_participants,get_participants, create_role, get_roles, create_user, get_users
urlpatterns = [
    path('upload', upload_data, name='upload_data'),
    path('dashboard', get_dashboard_data, name='get_dashboard_data'),
    path('batch_role', batch_role_summary, name='batch_role_summary'),
    path('learner_detail', learner_detail, name='learner_detail'),
    path('get_batches', get_batches, name='get_batches'),
    path('get_levels', get_levels, name='get_levels'),
    path('get_statuses', get_statuses, name='get_statuses'),
    path('download_file/<int:file_id>', download_file, name='download_file'),
    path('get_latest_uploads', get_latest_uploads, name='get_latest_uploads'),
    path('login', login, name='login'),
    path('manage_participants', manage_participants, name='manage_participants'),
    path('participant_data/', participant_data, name='participant_data'),
    path('send_query', send_query, name='send_query'),
    path('get_participants', get_participants, name= 'get_participants'),
    path('create_role', create_role, name= 'create_role'),
    path('get_roles', get_roles, name= 'get_roles'),
    path('create_user', create_user, name= 'create_user'),
    path('get_users', get_users, name= 'get_users'),

    ]
