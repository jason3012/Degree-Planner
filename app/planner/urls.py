from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = [
    path('status/', login_required(views.core_status), name='core_status'),
    path('offered/', login_required(views.offered_sections), name='offered_sections'),
]
