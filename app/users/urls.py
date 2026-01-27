from django.urls import path
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', login_required(views.dashboard), name='dashboard'),
]
