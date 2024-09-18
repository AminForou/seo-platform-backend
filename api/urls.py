from django.urls import path
from .views import check_url_status

urlpatterns = [
    path('check-url/', check_url_status, name='check_url_status'),
]
