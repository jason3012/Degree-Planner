from django.contrib import admin
from .models import Audit, AuditCourse


class AuditCourseInline(admin.TabularInline):
    model = AuditCourse
    extra = 0
    readonly_fields = ['course_code', 'term_code', 'credits', 'status', 'grade_token']


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'parse_version']
    list_filter = ['created_at', 'parse_version']
    search_fields = ['user__email']
    inlines = [AuditCourseInline]
    readonly_fields = ['created_at']


@admin.register(AuditCourse)
class AuditCourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'term_code', 'status', 'credits', 'grade_token', 'audit']
    list_filter = ['status', 'term_code', 'audit']
    search_fields = ['course_code', 'title_raw']
    raw_id_fields = ['audit']
