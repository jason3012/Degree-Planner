from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Audit, AuditCourse
from .parser import parse_audit_pdf


@login_required
def upload_audit(request):
    """Handle PDF upload and parsing."""
    if request.method == 'POST':
        if 'pdf_file' not in request.FILES:
            messages.error(request, 'Please select a PDF file.')
            return redirect('audit_upload')
        
        pdf_file = request.FILES['pdf_file']
        if not pdf_file.name.endswith('.pdf'):
            messages.error(request, 'Please upload a PDF file.')
            return redirect('audit_upload')
        
        # Create audit record
        audit = Audit.objects.create(
            user=request.user,
            uploaded_pdf=pdf_file
        )
        
        # Parse PDF
        try:
            courses = parse_audit_pdf(audit.uploaded_pdf.path)
            
            # Create AuditCourse records
            for course_data in courses:
                AuditCourse.objects.create(
                    audit=audit,
                    **course_data
                )
            
            messages.success(request, f'Successfully parsed {len(courses)} courses from audit.')
            return redirect('audit_confirm', audit_id=audit.id)
            
        except Exception as e:
            messages.error(request, f'Error parsing PDF: {str(e)}')
            audit.delete()
            return redirect('audit_upload')
    
    return render(request, 'audits/upload.html')


@login_required
def confirm_audit(request, audit_id):
    """Show extracted courses for confirmation/editing."""
    audit = get_object_or_404(Audit, id=audit_id, user=request.user)
    
    if request.method == 'POST':
        # Handle course updates/deletions
        if 'delete_course' in request.POST:
            course_id = request.POST.get('delete_course')
            AuditCourse.objects.filter(id=course_id, audit=audit).delete()
            messages.success(request, 'Course removed.')
            return redirect('audit_confirm', audit_id=audit.id)
        
        # Handle course edits
        course_updates = {}
        for key, value in request.POST.items():
            if key.startswith('course_'):
                parts = key.split('_')
                if len(parts) >= 3:
                    course_id = parts[1]
                    field = '_'.join(parts[2:])
                    if course_id not in course_updates:
                        course_updates[course_id] = {}
                    course_updates[course_id][field] = value
        
        for course_id, updates in course_updates.items():
            AuditCourse.objects.filter(id=course_id, audit=audit).update(**updates)
        
        if course_updates:
            messages.success(request, 'Courses updated.')
            return redirect('audit_confirm', audit_id=audit.id)
        
        # If confirmed, redirect to core status
        if 'confirm' in request.POST:
            return redirect('core_status')
    
    courses = audit.courses.all()
    context = {
        'audit': audit,
        'courses': courses,
    }
    return render(request, 'audits/confirm.html', context)
