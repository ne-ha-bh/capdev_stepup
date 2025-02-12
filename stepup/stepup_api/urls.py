from django.urls import path
from .views import upload_data

urlpatterns = [
    path('upload', upload_data, name='upload_data'),
    #path('dashboard1', get_dashboard1_data, name='get_dashboard1_data'),
]
