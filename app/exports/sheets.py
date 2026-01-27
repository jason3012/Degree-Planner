"""
Google Sheets export functionality.
"""
import os
from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_google_credentials(user):
    """Get or create Google OAuth credentials for user."""
    # This is simplified - in production, store tokens in user model or session
    # For MVP, we'll use a flow-based approach
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv('GOOGLE_CLIENT_ID', ''),
                "client_secret": os.getenv('GOOGLE_CLIENT_SECRET', ''),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/export/google-sheets/callback/')]
            }
        },
        scopes=settings.GOOGLE_SHEETS_SCOPES + settings.GOOGLE_DRIVE_SCOPES
    )
    
    # In production, retrieve stored credentials
    # For MVP, return None to trigger OAuth flow
    return None


def export_to_google_sheets(user):
    """
    Export core status and available sections to Google Sheets.
    
    Returns the URL of the created spreadsheet.
    """
    from app.audits.models import Audit, AuditCourse
    from app.catalog.models import Semester, Section
    from app.rules.engine import RequirementsEngine
    
    # Get audit data
    latest_audit = Audit.objects.filter(user=user).order_by('-created_at').first()
    if not latest_audit:
        raise ValueError("No audit found")
    
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
    
    # Get sections
    current_semester = Semester.objects.filter(is_current=True).first()
    if not current_semester:
        raise ValueError("No current semester set")
    
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
    
    # For MVP, this is a placeholder
    # In production, implement full OAuth flow and API calls
    raise NotImplementedError("Google Sheets export requires OAuth setup. See README for instructions.")
