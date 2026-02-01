from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
import csv
import io
from app.audits.models import Audit
from app.rules.engine import RequirementsEngine


@login_required
def export_dashboard(request):
    """Export options dashboard."""
    latest_audit = Audit.objects.filter(user=request.user).order_by('-created_at').first()
    context = {
        'audit': latest_audit,
    }
    return render(request, 'exports/dashboard.html', context)


@login_required
def export_csv_core_status(request):
    """Export core status as CSV from audit-driven core_requirements."""
    latest_audit = Audit.objects.filter(user=request.user).order_by('-created_at').first()
    if not latest_audit:
        messages.error(request, 'No audit found.')
        return redirect('export_dashboard')

    core_requirements = getattr(latest_audit, 'core_requirements', None) or {}
    if not isinstance(core_requirements, dict):
        core_requirements = {}

    rows = []
    for name, data in core_requirements.items():
        status = data.get('status', 'incomplete')
        completed = ', '.join(data.get('completed_courses') or data.get('satisfied_by') or [])
        remaining_to_plan = data.get('remaining_to_plan')
        remaining_to_complete = data.get('remaining_to_complete')
        remaining = ''
        if remaining_to_plan is not None and remaining_to_plan > 0:
            remaining = f"Remaining to plan: {remaining_to_plan} course(s)"
        if remaining_to_complete is not None and remaining_to_complete > 0 and remaining_to_complete != remaining_to_plan:
            remaining = (remaining + ' | Remaining to complete: ' + str(remaining_to_complete)) if remaining else f"Remaining to complete: {remaining_to_complete} course(s)"
        rows.append({
            'requirement_name': name,
            'status': status,
            'counted_so_far': completed,
            'remaining': remaining.strip(),
        })

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="core_status.csv"'
    writer = csv.DictWriter(response, fieldnames=['requirement_name', 'status', 'counted_so_far', 'remaining'])
    writer.writeheader()
    writer.writerows(rows)
    return response


@login_required
def export_csv_available_sections(request):
    """Export available sections as CSV."""
    from app.audits.models import AuditCourse
    from app.catalog.models import Semester, Section
    
    latest_audit = Audit.objects.filter(user=request.user).order_by('-created_at').first()
    if not latest_audit:
        messages.error(request, 'No audit found.')
        return redirect('export_dashboard')
    
    current_semester = Semester.objects.filter(is_current=True).first()
    if not current_semester:
        messages.error(request, 'No current semester set.')
        return redirect('export_dashboard')
    
    # Get needed courses
    completed_courses = set(AuditCourse.objects.filter(
        audit=latest_audit,
        status='completed'
    ).values_list('course_code', flat=True))
    
    in_progress_courses = set(AuditCourse.objects.filter(
        audit=latest_audit,
        status='in_progress'
    ).values_list('course_code', flat=True))
    
    engine = RequirementsEngine()
    evaluation = engine.evaluate(completed_courses, in_progress_courses)
    
    def extract_needed_codes(node_result):
        codes = set(node_result.get('still_needed', []))
        for child in node_result.get('children', []):
            codes.update(extract_needed_codes(child))
        return codes
    
    needed_codes = extract_needed_codes(evaluation)
    
    # Get sections
    sections = Section.objects.filter(
        semester=current_semester,
        course__course_code__in=needed_codes
    ).select_related('course', 'semester')
    
    # Create CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="available_sections.csv"'
    
    writer = csv.DictWriter(response, fieldnames=[
        'requirement_name', 'course_code', 'section_suffix', 'instructor',
        'days', 'start_time', 'end_time', 'location', 'term_code'
    ])
    writer.writeheader()
    
    for section in sections:
        meetings = section.meetings_json or {}
        writer.writerow({
            'requirement_name': 'Core Requirement',  # Simplified
            'course_code': section.course.course_code,
            'section_suffix': section.section_suffix,
            'instructor': section.instructor,
            'days': ', '.join(meetings.get('days', [])),
            'start_time': meetings.get('start_time', ''),
            'end_time': meetings.get('end_time', ''),
            'location': section.location,
            'term_code': section.semester.term_code,
        })
    
    return response


@login_required
def export_google_sheets(request):
    """Export to Google Sheets."""
    from app.exports.sheets import export_to_google_sheets
    
    try:
        sheet_url = export_to_google_sheets(request.user)
        messages.success(request, f'Successfully exported to Google Sheets: {sheet_url}')
        return JsonResponse({'success': True, 'url': sheet_url})
    except Exception as e:
        messages.error(request, f'Error exporting to Google Sheets: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
