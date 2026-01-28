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
            parsed = parse_audit_pdf(audit.uploaded_pdf.path)
            courses = parsed.get("transcript_courses", [])
            audit.core_requirements = parsed.get("core_requirements", {}) or {}
            audit.save(update_fields=["core_requirements"])

            # Deduplicate (term_code, course_code) to satisfy unique_together.
            # Some audits repeat the same course line multiple times across sections/pages.
            status_rank = {'withdrawn': 0, 'in_progress': 1, 'completed': 2}
            deduped = {}
            for course_data in courses:
                key = (course_data.get('term_code'), course_data.get('course_code'))
                existing = deduped.get(key)
                if not existing:
                    deduped[key] = course_data
                    continue

                # Keep the "best" status, prefer non-empty grade/title, keep max credits.
                if status_rank.get(course_data.get('status'), -1) > status_rank.get(existing.get('status'), -1):
                    existing['status'] = course_data.get('status')
                if not existing.get('grade_token') and course_data.get('grade_token'):
                    existing['grade_token'] = course_data.get('grade_token')
                if (course_data.get('title_raw') or '') and len(course_data.get('title_raw') or '') > len(existing.get('title_raw') or ''):
                    existing['title_raw'] = course_data.get('title_raw')
                try:
                    existing['credits'] = max(float(existing.get('credits', 0)), float(course_data.get('credits', 0)))
                except Exception:
                    pass

            # Create/update AuditCourse records (safe even if duplicates slip through)
            for (term_code, course_code), course_data in deduped.items():
                AuditCourse.objects.update_or_create(
                    audit=audit,
                    term_code=term_code,
                    course_code=course_code,
                    defaults=course_data,
                )
            
            messages.success(request, f'Successfully parsed {len(deduped)} courses from audit.')
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
    
    # Some historical parses may have written an out-of-range credit value into SQLite
    # (e.g., accidentally capturing the "1101" from a course code). SQLite can store it,
    # but Django's DecimalField converter may raise decimal.InvalidOperation on read.
    # If that happens, normalize credits for this audit and retry.
    try:
        courses = audit.courses.all()
        # Force evaluation here so we catch conversion errors before rendering.
        _ = len(courses)
    except Exception as e:
        if e.__class__.__name__ in {"InvalidOperation"}:
            AuditCourse.objects.filter(audit=audit).update(credits=3.0)
            courses = audit.courses.all()
        else:
            raise
    context = {
        'audit': audit,
        'courses': courses,
    }
    return render(request, 'audits/confirm.html', context)
