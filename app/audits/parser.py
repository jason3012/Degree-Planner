"""
Parse degree audit PDF to extract taken courses.
"""
import re
from typing import List, Dict, Any, Optional, Tuple


TERM_TOKEN_RE = re.compile(r"^(?P<yy>\d{2})(?P<term>FA|SP|SU|WI)\b", re.IGNORECASE)
TRANSCRIPT_LINE_RE = re.compile(
    r"^(?P<term>\d{2}(?:FA|SP|SU|WI))\s+"
    r"(?P<course>[A-Z]{4}\s*\d{4})\s+"
    r"(?P<credits>\d+(?:\.\d+)?)\s+"
    # Grade token MUST be consumed before title parsing:
    # - letter grades: A, A-, B+ ... (exactly [A-F][+-]?)
    # - special tokens: AP, IP, W, P
    # Use lookahead instead of \b so A- / B+ are handled correctly.
    r"(?P<grade>(?:AP|IP|W|P|[A-F][+-]?))(?=\s|$)"
    r"\s*(?P<rest>.*)$",
    re.IGNORECASE,
)


def _extract_pdf_text(pdf_path: str) -> str:
    try:
        import pypdf
        pdf_lib = 'pypdf'
    except ImportError:
        try:
            import pdfplumber
            pdf_lib = 'pdfplumber'
        except ImportError:
            raise ImportError("Need pypdf or pdfplumber to parse PDFs")
    
    # Extract text from PDF (preserve page order as best as possible)
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
    return text


def _normalize_term_token(token: str) -> str:
    token = token.upper().strip()
    # Already normalized like 26SP, 25FA, etc.
    return token


def _normalize_course_code(code: str) -> str:
    # "PSYC 1001" -> "PSYC1001"
    return re.sub(r"\s+", "", code.upper())


def _classify_grade(grade_token: str) -> Tuple[str, str]:
    g = (grade_token or "").upper().strip()
    if g == "IP":
        return "in_progress", "IP"
    if g == "W":
        return "withdrawn", "W"
    if g in {"AP", "P"}:
        return "completed", g
    # Letter grades
    if re.fullmatch(r"[A-F][+-]?", g):
        return "completed", g
    return "completed", ""


def parse_transcript_courses(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Transcript-like extraction.

    RULE: Only treat a line as an attempted course if it STARTS with a term token (YYFA/YYSP/YYSU/YYWI).
    Example line: 26SP CSCI2267 3.0 IP ...
    """
    courses: List[Dict[str, Any]] = []
    for raw in lines:
        line = (raw or "").strip()
        if not line:
            continue
        if "My Audit - Audit Results Tab" in line:
            continue

        m = TRANSCRIPT_LINE_RE.match(line)
        if not m:
            continue

        term_code = _normalize_term_token(m.group("term"))
        course_code = _normalize_course_code(m.group("course"))
        credits = float(m.group("credits"))
        grade_token = (m.group("grade") or "").upper()
        status, grade_token = _classify_grade(grade_token)
        title_raw = (m.group("rest") or "").strip()

        # Keep title reasonably clean
        title_raw = re.sub(r"\s+", " ", title_raw)[:200]

        courses.append(
            {
                "term_code": term_code,
                "course_code": course_code,
                "credits": round(credits, 1),
                "status": status,
                "grade_token": grade_token,
                "title_raw": title_raw,
            }
        )
    return courses


def _is_core_section_start(line: str) -> bool:
    return "University Core Requirements" in line


def _is_core_section_end(line: str) -> bool:
    # Stop at next major section header.
    return "Intermediate Proficiency" in line


CORE_BUCKETS = [
    "Writing",
    "Literature",
    "Arts",
    "Social Science",
    "History I",
    "History II",
    "Natural Science",
    "Philosophy",
    "Theology I",
    "Theology II",
    "Cultural Diversity",
    "Global Engagement",
    "Language Proficiency",
    "Mathematics",
]


def _match_bucket_heading(line: str) -> Optional[str]:
    # Exact match against known buckets, and a few flexible variants.
    normalized = re.sub(r"\s+", " ", line).strip()
    for b in CORE_BUCKETS:
        if normalized.lower() == b.lower():
            return b
    # Handle headings like "History II (Modern)" → startswith "History II"
    for b in CORE_BUCKETS:
        if normalized.lower().startswith(b.lower() + " "):
            return b
    return None


def _parse_needs_count(line: str) -> Optional[int]:
    # Examples: "NEEDS: 1 COURSE" / "NEEDS: 2 COURSES"
    m = re.search(r"\bNEEDS:\s*(\d+)\b", line.upper())
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _extract_option_patterns(text: str) -> List[Dict[str, Any]]:
    """
    Normalize core option codes into:
    - exact: PSYC1001
    - range: subject SOCY, start 1001, end 1099
    - wildcard: subject POLI, pattern 10** (kept as string)
    """
    out: List[Dict[str, Any]] = []

    # Ranges: "SOCY 1001 TO 1099"
    for m in re.finditer(r"\b([A-Z]{4})\s*(\d{4})\s+TO\s+(\d{4})\b", text.upper()):
        out.append({"type": "range", "subject": m.group(1), "start": m.group(2), "end": m.group(3)})

    # Wildcards: "POLI 10**" or "EESC 2***"
    for m in re.finditer(r"\b([A-Z]{4})\s*((?:\d\*{2,3})|(?:\d{2}\*{2}))\b", text.upper()):
        out.append({"type": "wildcard", "subject": m.group(1), "pattern": m.group(2)})

    # Exact: "PSYC 1001"
    for m in re.finditer(r"\b([A-Z]{4})\s*(\d{4})\b", text.upper()):
        code = f"{m.group(1)}{m.group(2)}"
        out.append({"type": "exact", "code": code})

    # Dedup while preserving order
    seen = set()
    deduped = []
    for item in out:
        key = tuple(sorted(item.items()))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def parse_core_requirements(lines: List[str]) -> Dict[str, Any]:
    """
    Core requirement extraction via a state machine.

    - Restrict parsing to the 'University Core Requirements...' section.
    - Within that, parse per-bucket status via semantic cues (NEEDS, IP, completed course lines).
    - Treat 'SELECT FROM:' as a multiline block until next bucket heading.
    """
    in_core_section = False
    current_bucket: Optional[str] = None
    collecting_select_from = False
    select_from_buffer: List[str] = []

    out: Dict[str, Any] = {}

    def ensure_bucket(name: str) -> Dict[str, Any]:
        if name not in out:
            out[name] = {
                "status": "unknown",
                "needs": None,
                "satisfied_by": [],
                "in_progress": [],
                "withdrawn": [],
                "options_raw": [],
                "options": [],
            }
        return out[name]

    for raw in lines:
        line = (raw or "").strip()
        if not line:
            continue
        if "My Audit - Audit Results Tab" in line:
            continue

        if not in_core_section:
            if _is_core_section_start(line):
                in_core_section = True
            continue

        # End condition
        if _is_core_section_end(line):
            break

        # Bucket heading detection
        bucket = _match_bucket_heading(line)
        if bucket:
            # finalize previous select-from
            if collecting_select_from and current_bucket:
                b = ensure_bucket(current_bucket)
                text = " ".join(select_from_buffer)
                b["options_raw"].append(text)
                b["options"].extend(_extract_option_patterns(text))
            collecting_select_from = False
            select_from_buffer = []
            current_bucket = bucket
            ensure_bucket(bucket)
            continue

        if not current_bucket:
            continue

        b = ensure_bucket(current_bucket)

        # NEEDS ⇒ incomplete
        needs = _parse_needs_count(line)
        if needs is not None:
            b["needs"] = needs
            b["status"] = "incomplete"
            continue

        # SELECT FROM block
        if "SELECT FROM" in line.upper():
            collecting_select_from = True
            # Keep anything after the colon too
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            select_from_buffer = [after] if after else []
            # status stays incomplete if we already saw NEEDS, otherwise assume incomplete
            if b["status"] == "unknown":
                b["status"] = "incomplete"
            continue

        if collecting_select_from:
            # Stop collecting if we hit something that looks like a new section header.
            # (Bucket headings are handled above; this is a fallback.)
            if TERM_TOKEN_RE.match(line) or line.isupper():
                # term lines inside select-from are unlikely; end block conservatively
                collecting_select_from = False
            else:
                select_from_buffer.append(line)
                continue

        # Course lines within bucket: use same transcript line rule (term-coded at start)
        m = TRANSCRIPT_LINE_RE.match(line)
        if m:
            term_code = _normalize_term_token(m.group("term"))
            course_code = _normalize_course_code(m.group("course"))
            grade_token = (m.group("grade") or "").upper()
            status, grade_token = _classify_grade(grade_token)
            if status == "in_progress":
                b["status"] = "in_progress" if b["status"] != "satisfied" else b["status"]
                b["in_progress"].append(f"{course_code}({term_code})")
            elif status == "withdrawn":
                b["withdrawn"].append(f"{course_code}({term_code})")
            else:
                b["status"] = "satisfied" if b["status"] != "incomplete" else b["status"]
                suffix = grade_token or "COMPLETED"
                b["satisfied_by"].append(f"{course_code}({suffix})")
            continue

        # If we see an isolated IP marker, treat bucket as in progress (fallback cue)
        if re.search(r"\bIP\b", line.upper()) and b["status"] == "unknown":
            b["status"] = "in_progress"

    # finalize trailing select-from
    if collecting_select_from and current_bucket:
        b = ensure_bucket(current_bucket)
        text = " ".join(select_from_buffer)
        b["options_raw"].append(text)
        b["options"].extend(_extract_option_patterns(text))

    return out


def parse_audit_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Parse audit PDF and return TWO outputs:
      A) transcript_courses: attempted courses (term-coded line only)
      B) core_requirements: core bucket status + option patterns (section-restricted)
    """
    text = _extract_pdf_text(pdf_path)
    lines = text.splitlines()

    transcript_courses = parse_transcript_courses(lines)
    core_requirements = parse_core_requirements(lines)

    return {
        "transcript_courses": transcript_courses,
        "core_requirements": core_requirements,
    }
