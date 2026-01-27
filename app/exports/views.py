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
    """Export core status as CSV."""
    from app.audits.models import AuditCourse
    
    latest_audit = Audit.objects.filter(user=request.user).order_by('-created_at').first()
    if not latest_audit:
        messages.error(request, 'No audit found.')
        return redirect('export_dashboard')
    
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
    
    # Flatten requirements for CSV
    def flatten_requirements(node_result, name='Root', rows=None):
        if rows is None:
            rows = []
        
        status = node_result.get('status', 'missing')
        satisfied_by = ', '.join(node_result.get('satisfied_by', []))
        still_needed = ', '.join(node_result.get('still_needed', []))
        
        rows.append({
            'requirement_name': name,
            'status': status,
            'satisfied_by': satisfied_by,
            'still_needed': still_needed,
        })
        
        # Handle children - they're already evaluated results, not configs
        children = node_result.get('children', [])
        if children and isinstance(children[0], dict) and 'name' in children[0]:
            # Children have names
            for child in children:
                child_name = child.get('name', 'Child')
                flatten_requirements(child, f"{name} > {child_name}", rows)
        elif children:
            # Children are just results
            for i, child in enumerate(children):
                flatten_requirements(child, f"{name} > Requirement {i+1}", rows)
        
        return rows
    
    rows = flatten_requirements(evaluation)
    
    # Create CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="core_status.csv"'
    
    writer = csv.DictWriter(response, fieldnames=['requirement_name', 'status', 'satisfied_by', 'still_needed'])
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
