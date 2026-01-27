"""
Parse degree audit PDF to extract taken courses.
"""
import re
from typing import List, Dict


def parse_audit_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse audit PDF and extract courses.
    
    Expected format: lines starting with term tokens like 26SP, 25FA, 21SU
    Then parse: term, course code, credits, status, title
    
    Returns list of course dictionaries.
    """
    try:
        import pypdf
        pdf_lib = 'pypdf'
    except ImportError:
        try:
            import pdfplumber
            pdf_lib = 'pdfplumber'
        except ImportError:
            raise ImportError("Need pypdf or pdfplumber to parse PDFs")
    
    # Extract text from PDF
    text = ""
    if pdf_lib == 'pypdf':
        import pypdf
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    else:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    
    courses = []
    lines = text.split('\n')
    
    # Pattern for term codes: YYSP, YYFA, YYSU, YYWI (e.g., 26SP, 25FA)
    term_pattern = r'^(\d{2})(SP|FA|SU|WI|SPRING|FALL|SUMMER|WINTER)'
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for term token
        term_match = re.match(term_pattern, line, re.IGNORECASE)
        if term_match:
            year = term_match.group(1)
            term_abbr = term_match.group(2).upper()
            
            # Normalize term code
            term_map = {
                'SP': 'SP', 'SPRING': 'SP',
                'FA': 'FA', 'FALL': 'FA',
                'SU': 'SU', 'SUMMER': 'SU',
                'WI': 'WI', 'WINTER': 'WI'
            }
            term_code = f"{year}{term_map.get(term_abbr, term_abbr[:2])}"
            
            # Look ahead for course code
            course_data = None
            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                
                # Look for course code pattern: ABCD1234
                course_match = re.match(r'^([A-Z]{4}\d{4})', next_line)
                if course_match:
                    course_code = course_match.group(1)
                    
                    # Extract credits (look for decimal number)
                    credits_match = re.search(r'(\d+\.?\d*)', next_line)
                    credits = float(credits_match.group(1)) if credits_match else 3.0
                    
                    # Extract status/grade
                    status = 'completed'
                    grade_token = ''
                    
                    # Check for status indicators
                    status_line = next_line.upper()
                    if 'IP' in status_line or 'IN PROGRESS' in status_line:
                        status = 'in_progress'
                        grade_token = 'IP'
                    elif 'W' in status_line and ('WITHDRAW' in status_line or re.search(r'\bW\b', status_line)):
                        status = 'withdrawn'
                        grade_token = 'W'
                    elif 'AP' in status_line:
                        status = 'completed'
                        grade_token = 'AP'
                    elif 'P' in status_line and 'PASS' in status_line:
                        status = 'completed'
                        grade_token = 'P'
                    else:
                        # Look for letter grades
                        grade_match = re.search(r'\b([A-F][+-]?)\b', status_line)
                        if grade_match:
                            grade_token = grade_match.group(1)
                            status = 'completed'
                    
                    # Extract title (rest of line or next line)
                    title = next_line.replace(course_code, '').strip()
                    title = re.sub(r'\d+\.?\d*', '', title).strip()  # Remove credits
                    title = re.sub(r'\b(IP|W|AP|P|[A-F][+-]?)\b', '', title, flags=re.IGNORECASE).strip()
                    
                    if not title and j + 1 < len(lines):
                        title = lines[j + 1].strip()
                    
                    course_data = {
                        'term_code': term_code,
                        'course_code': course_code,
                        'credits': credits,
                        'status': status,
                        'grade_token': grade_token,
                        'title_raw': title[:200]  # Truncate
                    }
                    break
            
            if course_data:
                courses.append(course_data)
        
        i += 1
    
    return courses
