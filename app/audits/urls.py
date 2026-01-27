from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = [
    path('upload/', login_required(views.upload_audit), name='audit_upload'),
    path('confirm/<int:audit_id>/', login_required(views.confirm_audit), name='audit_confirm'),
]
