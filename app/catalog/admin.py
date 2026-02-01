from django.contrib import admin
from .models import Semester, Course, Section, CoreTag


@admin.register(CoreTag)
class CoreTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['term_code', 'label', 'is_current', 'created_at']
    list_filter = ['is_current']
    search_fields = ['term_code', 'label']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'title', 'credits', 'department', 'level']
    search_fields = ['course_code', 'title', 'department']
    list_filter = ['level', 'department']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['full_code', 'semester', 'instructor', 'location', 'status']
    list_filter = ['semester', 'status', 'course', 'core_tags']
    search_fields = ['course__course_code', 'instructor', 'location']
    raw_id_fields = ['semester', 'course']
    filter_horizontal = ['core_tags']
