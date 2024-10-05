from django.urls import path
from .views import check_url_status, ContactMessageView, ProcessCSVView  # Ensure this import is correct

urlpatterns = [
    path('check-url/', check_url_status, name='check_url_status'),
    path('contact/', ContactMessageView.as_view(), name='contact'),
    path('process-csv/', ProcessCSVView.as_view(), name='process-csv'),

]