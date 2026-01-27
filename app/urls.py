"""
URL configuration for degreeplanner project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
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
