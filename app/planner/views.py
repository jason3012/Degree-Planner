from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from app.audits.models import Audit
from app.catalog.models import Semester, Section
from app.rules.engine import RequirementsEngine


@login_required
def core_status(request):
    """Show core requirement status."""
    from django.contrib import messages
    from app.audits.models import AuditCourse
    
    # Get latest audit
    latest_audit = Audit.objects.filter(user=request.user).order_by('-created_at').first()
    if not latest_audit:
        messages.warning(request, 'Please upload your degree audit first.')
        return redirect('audit_upload')
    
    # Get completed and in-progress courses
    completed_courses = AuditCourse.objects.filter(
        audit=latest_audit,
        status='completed'
    ).values_list('course_code', flat=True)
    
    in_progress_courses = AuditCourse.objects.filter(
        audit=latest_audit,
        status='in_progress'
    ).values_list('course_code', flat=True)
    
    # Evaluate requirements
    engine = RequirementsEngine()
    evaluation = engine.evaluate(set(completed_courses), set(in_progress_courses))
    
    context = {
        'audit': latest_audit,
        'evaluation': evaluation,
        'completed_count': len(completed_courses),
        'in_progress_count': len(in_progress_courses),
    }
    return render(request, 'planner/core_status.html', context)


@login_required
def offered_sections(request):
    """Show offered sections for remaining core requirements."""
    from django.contrib import messages
    from app.audits.models import AuditCourse
    
    # Get latest audit
    latest_audit = Audit.objects.filter(user=request.user).order_by('-created_at').first()
    if not latest_audit:
        messages.warning(request, 'Please upload your degree audit first.')
        return redirect('audit_upload')
    
    # Get current semester
    current_semester = Semester.objects.filter(is_current=True).first()
    if not current_semester:
        messages.warning(request, 'No current semester set. Please contact administrator.')
        return redirect('dashboard')
    
    # Get completed and in-progress courses
    completed_courses = set(AuditCourse.objects.filter(
        audit=latest_audit,
        status='completed'
    ).values_list('course_code', flat=True))
    
    in_progress_courses = set(AuditCourse.objects.filter(
        audit=latest_audit,
        status='in_progress'
    ).values_list('course_code', flat=True))
    
    # Evaluate requirements
    engine = RequirementsEngine()
    evaluation = engine.evaluate(completed_courses, in_progress_courses)
    
    # Extract still needed course codes
    def extract_needed_codes(node_result):
        codes = set(node_result.get('still_needed', []))
        for child in node_result.get('children', []):
            codes.update(extract_needed_codes(child))
        return codes
    
    needed_codes = extract_needed_codes(evaluation)
    
    # Get sections for needed courses
    sections = Section.objects.filter(
        semester=current_semester,
        course__course_code__in=needed_codes
    ).select_related('course', 'semester').order_by('course__course_code', 'section_suffix')
    
    # Group by requirement
    requirement_sections = {}
    for code in needed_codes:
        # Find which requirement this code belongs to
        requirement_name = _find_requirement_for_code(code, evaluation)
        if requirement_name not in requirement_sections:
            requirement_sections[requirement_name] = []
        
        code_sections = sections.filter(course__course_code=code)
        requirement_sections[requirement_name].extend(code_sections)
    
    # Apply filters
    day_filter = request.GET.get('day', '')
    time_start = request.GET.get('time_start', '')
    time_end = request.GET.get('time_end', '')
    
    if day_filter or time_start or time_end:
        filtered_sections = {}
        for req_name, req_sections in requirement_sections.items():
            filtered = []
            for section in req_sections:
                meetings = section.meetings_json or {}
                days = meetings.get('days', [])
                
                # Day filter
                if day_filter and day_filter not in [d[:2] for d in days]:
                    continue
                
                # Time filter
                if time_start or time_end:
                    start_time = meetings.get('start_time', '')
                    if time_start and start_time < time_start:
                        continue
                    if time_end and start_time > time_end:
                        continue
                
                filtered.append(section)
            filtered_sections[req_name] = filtered
        requirement_sections = filtered_sections
    
    context = {
        'audit': latest_audit,
        'evaluation': evaluation,
        'requirement_sections': requirement_sections,
        'current_semester': current_semester,
        'day_filter': day_filter,
        'time_start': time_start,
        'time_end': time_end,
    }
    return render(request, 'planner/offered_sections.html', context)


def _find_requirement_for_code(code: str, evaluation: dict) -> str:
    """Find which requirement a course code belongs to."""
    def search_node(node_result, code):
        if code in node_result.get('still_needed', []):
            return node_result.get('name', 'Unknown')
        for child in node_result.get('children', []):
            result = search_node(child, code)
            if result:
                return result
        return None
    
    return search_node(evaluation, code) or 'Other'
