from django.urls import path
from .views import upload_data, user_details, get_participant_details, get_candidates_in_progress, get_fail_candidates, get_pass_candidates, get_total_invites

urlpatterns = [
    path('upload', upload_data, name='upload_data'),
    path('user-details', user_details, name='user_details'),
    path('participant-details', get_participant_details, name='get_participant_details'),
    path('in-progress-candidate', get_candidates_in_progress, name='get_candidates_in_progress'),
    path('fail-candidates', get_fail_candidates, name='get_fail_candidates'),
    path('pass-candidates', get_pass_candidates, name='get_pass_candidates'),
    path('invited-candidates', get_total_invites, name='get_total_invites'),
]
