"""
Import catalog CSV into database.
"""
import csv
import re
from typing import Dict, Optional
from django.core.management.base import BaseCommand
from django.db import transaction
from app.catalog.models import Semester, Course, Section


def normalize_term(semester_str: str) -> tuple[str, str]:
    """
    Convert semester string to term_code and label.
    Examples:
        "Spring 2026" -> ("26SP", "Spring 2026")
        "Fall 2025" -> ("25FA", "Fall 2025")
    """
    semester_str = semester_str.strip()
    
    # Extract year
    year_match = re.search(r'(\d{4})', semester_str)
    if not year_match:
        raise ValueError(f"Could not extract year from: {semester_str}")
    
    year = year_match.group(1)
    year_short = year[-2:]  # Last 2 digits
    
    # Determine term
    semester_lower = semester_str.lower()
    if 'spring' in semester_lower:
        term_code = f"{year_short}SP"
    elif 'fall' in semester_lower:
        term_code = f"{year_short}FA"
    elif 'summer' in semester_lower:
        term_code = f"{year_short}SU"
    elif 'winter' in semester_lower:
        term_code = f"{year_short}WI"
    else:
        raise ValueError(f"Could not determine term from: {semester_str}")
    
    return term_code, semester_str


def parse_course_code(full_code: str) -> tuple[str, str]:
    """
    Split course code like ABCD0123.01 into base_code and section_suffix.
    Returns: (base_code, section_suffix)
    """
    # Handle format: ABCD0123.01 or ABCD012301
    if '.' in full_code:
        parts = full_code.split('.')
        base_code = parts[0]
        section_suffix = parts[1] if len(parts) > 1 else '01'
    else:
        # Check if it's 10 characters (ABCD012301 -> ABCD0123.01)
        if len(full_code) == 10 and full_code[:4].isalpha() and full_code[4:].isdigit():
            base_code = full_code[:8]
            section_suffix = full_code[8:]
        else:
            # Assume it's just base code
            base_code = full_code
            section_suffix = '01'
    
    # Validate base code format
    if not re.match(r'^[A-Z]{4}\d{4}$', base_code):
        raise ValueError(f"Invalid course code format: {base_code}")
    
    return base_code, section_suffix


def parse_meeting_text(meeting_str: str) -> Dict:
    """
    Parse meeting string to extract days, times, location.
    Example: "Stokes Hall 105S TuTh 01:30PM-02:45PM"
    Returns dict with days, start_time, end_time, location.
    """
    if not meeting_str:
        return {}
    
    result = {
        'days': [],
        'start_time': '',
        'end_time': '',
        'location': ''
    }
    
    # Day abbreviations
    day_map = {
        'M': 'Monday',
        'Tu': 'Tuesday',
        'T': 'Tuesday',
        'W': 'Wednesday',
        'Th': 'Thursday',
        'R': 'Thursday',
        'F': 'Friday',
        'Sa': 'Saturday',
        'Su': 'Sunday'
    }
    
    # Extract days
    day_pattern = r'\b(M|Tu|T|W|Th|R|F|Sa|Su)\b'
    days_found = re.findall(day_pattern, meeting_str)
    result['days'] = [day_map.get(d, d) for d in days_found if d in day_map]
    
    # Extract time range
    time_pattern = r'(\d{1,2}:\d{2}(?:AM|PM))-(\d{1,2}:\d{2}(?:AM|PM))'
    time_match = re.search(time_pattern, meeting_str)
    if time_match:
        result['start_time'] = time_match.group(1)
        result['end_time'] = time_match.group(2)
    
    # Extract location (everything before days or times)
    location_parts = []
    for part in meeting_str.split():
        if not re.match(day_pattern, part) and not re.match(r'\d{1,2}:\d{2}(?:AM|PM)', part):
            location_parts.append(part)
        else:
            break
    result['location'] = ' '.join(location_parts)
    
    return result


def import_catalog_csv(csv_path: str, semester_str: str, is_current: bool = False):
    """
    Import catalog CSV file.
    
    Expected CSV columns:
    - course_code (e.g., ARTS1101.01)
    - course_name
    - professor
    - semester
    - course_description
    - credits
    - room_and_schedule
    - satisfies_core_requirement
    - prerequisites
    - corequisites
    - cross_listed_with
    - student_level
    """
    term_code, label = normalize_term(semester_str)
    
    # Get or create semester
    semester, created = Semester.objects.get_or_create(
        term_code=term_code,
        defaults={'label': label, 'is_current': is_current}
    )
    if created:
        print(f"Created semester: {semester}")
    else:
        semester.label = label
        semester.is_current = is_current
        semester.save()
        print(f"Updated semester: {semester}")
    
    imported_count = 0
    error_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        with transaction.atomic():
            for row in reader:
                try:
                    full_code = row.get('course_code', '').strip()
                    if not full_code:
                        continue
                    
                    # Parse course code
                    base_code, section_suffix = parse_course_code(full_code)
                    
                    # Get or create course
                    course, _ = Course.objects.get_or_create(
                        course_code=base_code,
                        defaults={
                            'title': row.get('course_name', '')[:200],
                            'description': row.get('course_description', ''),
                            'credits': float(row.get('credits', 3.0) or 3.0),
                            'department': base_code[:4],  # First 4 letters
                            'level': 'undergraduate' if 'undergraduate' in row.get('student_level', '').lower() else 'graduate'
                        }
                    )
                    
                    # Update course info if available
                    if row.get('course_name'):
                        course.title = row.get('course_name')[:200]
                    if row.get('course_description'):
                        course.description = row.get('course_description')
                    if row.get('credits'):
                        try:
                            course.credits = float(row.get('credits'))
                        except:
                            pass
                    course.save()
                    
                    # Parse meeting info
                    meeting_text = row.get('room_and_schedule', '')
                    meetings_data = parse_meeting_text(meeting_text)
                    
                    # Get or create section
                    section, created = Section.objects.get_or_create(
                        semester=semester,
                        course=course,
                        section_suffix=section_suffix,
                        defaults={
                            'instructor': row.get('professor', ''),
                            'raw_meeting_text': meeting_text,
                            'meetings_json': meetings_data,
                            'location': meetings_data.get('location', ''),
                        }
                    )
                    
                    if not created:
                        # Update existing section
                        section.instructor = row.get('professor', '')
                        section.raw_meeting_text = meeting_text
                        section.meetings_json = meetings_data
                        section.location = meetings_data.get('location', '')
                        section.save()
                    
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"Error importing row {full_code}: {e}")
                    continue
    
    print(f"\nImport complete:")
    print(f"  Imported: {imported_count} sections")
    print(f"  Errors: {error_count}")
    return imported_count, error_count


class Command(BaseCommand):
    help = 'Import catalog CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to catalog CSV file')
        parser.add_argument('--semester', type=str, required=True, help='Semester label (e.g., "Spring 2026")')
        parser.add_argument('--current', action='store_true', help='Mark as current semester')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        semester = options['semester']
        is_current = options.get('current', False)
        
        self.stdout.write(f"Importing catalog from {csv_file}...")
        imported, errors = import_catalog_csv(csv_file, semester, is_current)
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {imported} sections'))
