from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = [
    path('', login_required(views.assistant_chat), name='assistant_chat'),
    path('query/', login_required(views.assistant_query), name='assistant_query'),
]
