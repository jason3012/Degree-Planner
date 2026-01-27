from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = [
    path('', login_required(views.export_dashboard), name='export_dashboard'),
    path('csv/core-status/', login_required(views.export_csv_core_status), name='export_csv_core_status'),
    path('csv/available-sections/', login_required(views.export_csv_available_sections), name='export_csv_available_sections'),
    path('google-sheets/', login_required(views.export_google_sheets), name='export_google_sheets'),
]
