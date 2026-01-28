"""
URL configuration for degreeplanner project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Redirect regular login/signup to Google OAuth
    path('accounts/login/', RedirectView.as_view(url='/accounts/google/login/', permanent=False), name='account_login'),
    path('accounts/signup/', RedirectView.as_view(url='/accounts/google/login/', permanent=False), name='account_signup'),
    path('accounts/', include('allauth.urls')),
    path('', include('app.users.urls')),
    path('dashboard/', include('app.users.urls')),
    path('audit/', include('app.audits.urls')),
    path('core/', include('app.planner.urls')),
    path('export/', include('app.exports.urls')),
    path('assistant/', include('app.assistant.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
