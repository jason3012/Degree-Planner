"""
Grounded AI assistant using Gemini.
"""
import os
import json
from django.conf import settings
from app.audits.models import Audit, AuditCourse
from app.catalog.models import Semester, Section
from app.rules.engine import RequirementsEngine


def get_ai_recommendation(user, query: str, constraints: dict = None):
    """
    Get AI recommendation based on requirements and available sections.
    
    The AI is grounded - it can only recommend sections that exist.
    """
    if constraints is None:
        constraints = {}
    
    # Get audit data
    latest_audit = Audit.objects.filter(user=user).order_by('-created_at').first()
    if not latest_audit:
        return "Please upload your degree audit first."
    
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
    
    # Get available sections
    current_semester = Semester.objects.filter(is_current=True).first()
    if not current_semester:
        return "No current semester is set."
    
    def extract_needed_codes(node_result):
        codes = set(node_result.get('still_needed', []))
        for child in node_result.get('children', []):
            codes.update(extract_needed_codes(child))
        return codes
    
    needed_codes = extract_needed_codes(evaluation)
    sections = Section.objects.filter(
        semester=current_semester,
        course__course_code__in=needed_codes
    ).select_related('course', 'semester')
    
    # Format sections for AI
    sections_data = []
    for section in sections:
        meetings = section.meetings_json or {}
        sections_data.append({
            'course_code': section.full_code,
            'course_name': section.course.title,
            'instructor': section.instructor,
            'days': meetings.get('days', []),
            'start_time': meetings.get('start_time', ''),
            'end_time': meetings.get('end_time', ''),
            'location': section.location,
        })
    
    # Prepare context for AI
    context = {
        'requirements_status': evaluation,
        'available_sections': sections_data,
        'constraints': constraints,
        'completed_courses': list(completed_courses),
        'in_progress_courses': list(in_progress_courses),
    }
    
    # Call Gemini API
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return "AI assistant is not configured. Please set GEMINI_API_KEY in settings."
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""You are a degree planning assistant. Based on the following information, help the student with their query.

Requirements Status:
{json.dumps(evaluation, indent=2)}

Available Sections:
{json.dumps(sections_data, indent=2)}

User Constraints:
{json.dumps(constraints, indent=2)}

User Query: {query}

IMPORTANT: You can ONLY recommend sections that are in the Available Sections list above. Do not suggest courses that are not available.

Provide a helpful, concise response."""
        
        response = model.generate_content(prompt)
        return response.text
        
    except ImportError:
        return "Google Generative AI library not installed. Install with: pip install google-generativeai"
    except Exception as e:
        return f"Error getting AI recommendation: {str(e)}"
