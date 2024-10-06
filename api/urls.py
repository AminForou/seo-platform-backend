from django.urls import path
from .views import check_url_status  # Only import what's needed from views.py
from .contact_view import ContactMessageView  # Import from contact_views.py
from .csv_views import ProcessCSVView  # Import from csv_views.py

urlpatterns = [
    path('check-url/', check_url_status, name='check_url_status'),
    path('contact/', ContactMessageView.as_view(), name='contact'),
    path('process-csv/', ProcessCSVView.as_view(), name='process-csv'),
]