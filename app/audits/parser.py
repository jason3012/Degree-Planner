"""
Parse degree audit PDF to extract taken courses.

Source of truth: The audit PDF. "What counts so far" comes only from courses
listed under each core heading in the audit. The catalog is used only for
recommendations (e.g. filter Spring sections by SELECT FROM patterns), not for
deciding what already counted.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


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
    """Start parsing only after header containing both 'University Core Requirements' and 'Morrissey'."""
    if not line:
        return False
    return "University Core Requirements" in line and "Morrissey" in line


# Core window stop markers (report section delimiters). Stop immediately on any of these.
CORE_WINDOW_STOP_MARKERS = [
    "Intermediate Proficiency",
    "Major Requirements",
    "Component (",  # e.g. "Mathematics Component (12 hours)"
    "Elective Courses Counting Toward Degree Credits",
    "Courses Not Counting Toward Degree Credits",
]


def _is_core_section_end(line: str) -> bool:
    """Stop immediately when seeing the next major header (core window end)."""
    if not (line or "").strip():
        return False
    normalized = (line or "").strip()
    for marker in CORE_WINDOW_STOP_MARKERS:
        if marker in normalized:
            return True
    return False


# Whitelist: only these count as core headings within the core window.
# "Mathematics Component (12 hours)" etc. must NOT match.
CORE_HEADING_WHITELIST = [
    "Writing",
    "Literature",
    "Arts",
    "Mathematics",
    "History I",
    "History II",
    "Philosophy",
    "Social Science",
    "Natural Science",
    "Theology",  # appears as Theology: PULSE Perspectives or Legacy, or Theology I/II
    "Cultural Diversity",
]


def _is_requirement_header_whitelist(line: str) -> Optional[str]:
    """
    Treat as requirement header only if it is one of the known core labels.
    "Mathematics Component (12 hours)" must NOT match (handled by stop marker).
    """
    normalized = re.sub(r"\s+", " ", (line or "").strip())
    if not normalized:
        return None
    lower = normalized.lower()
    for h in CORE_HEADING_WHITELIST:
        if lower == h.lower():
            return h
    if lower.startswith("theology"):
        if lower == "theology":
            return "Theology"
        if lower.startswith("theology:"):
            return "Theology"
        if lower.startswith("theology ii") or lower == "theology ii":
            return "Theology"
        if lower.startswith("theology i ") or lower == "theology i":
            return "Theology"
    return None


def _is_requirement_header_fallback(line: str) -> bool:
    """Fallback: short (<= 6 words), Title Case, no term token prefix, not SELECT FROM / NEEDS."""
    if not line or len(line) > 80:
        return False
    stripped = (line or "").strip()
    if not stripped:
        return False
    if "SELECT FROM" in stripped.upper() or stripped.upper().startswith("NEEDS"):
        return False
    if TERM_TOKEN_RE.match(stripped):
        return False
    words = re.split(r"\s+", stripped)
    if len(words) > 6:
        return False
    # Title Case: first letter of each word upper (loose check)
    if words and words[0] and words[0][0].isupper():
        return True
    return False


def _match_bucket_heading(line: str) -> Optional[str]:
    """Requirement header: only whitelist (known core labels). No fallback bucket creation."""
    return _is_requirement_header_whitelist(line)


# Only NEEDS: N COURSE(S) — ignore NEEDS: N SUB-REQS (summary line).
NEEDS_COURSE_RE = re.compile(r"\bNEEDS:\s*(\d+)\s*COURSE(?:S)?\b", re.IGNORECASE)


def _parse_needs_courses(line: str) -> Optional[int]:
    """Parse remaining count only from NEEDS: N COURSE(S). Do not treat NEEDS: N SUB-REQS as per-core need."""
    m = NEEDS_COURSE_RE.search(line or "")
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


def _normalize_core_output(
    out: Dict[str, Any], line_indices: Optional[Dict[str, Tuple[int, int]]] = None
) -> Dict[str, Any]:
    """
    Normalize each bucket. Do NOT use SELECT FROM for status or eligibility (debug only).
    Compute required_total, remaining_to_plan, remaining_to_complete without hardcoding required counts.
    """
    result: Dict[str, Any] = {}
    for name, b in out.items():
        completed_list = b.get("completed_courses", [])
        in_progress_list = b.get("in_progress_courses", [])
        needs_courses = b.get("needs_courses")  # from NEEDS: N COURSE(S) only; may be None
        select_raw = b.get("select_from_raw")  # debug only; not used for status or eligibility

        completed = len(completed_list)
        ip = len(in_progress_list)

        if needs_courses is not None:
            required_total = completed + ip + needs_courses
        else:
            required_total = completed + ip

        remaining_to_plan = max(0, required_total - (completed + ip))
        remaining_to_complete = max(0, required_total - completed)

        if remaining_to_complete == 0:
            status = "complete"
        elif remaining_to_plan == 0 and ip > 0:
            status = "in_progress"
        else:
            status = "incomplete"

        result[name] = {
            "status": status,
            "completed_courses": completed_list,
            "in_progress_courses": in_progress_list,
            "needs_courses": needs_courses,
            "required_total": required_total,
            "remaining_to_plan": remaining_to_plan,
            "remaining_to_complete": remaining_to_complete,
            "select_from_raw": select_raw,
        }
    return result


def _log_core_debug(
    out: Dict[str, Any],
    line_indices: Dict[str, Tuple[int, int]],
    select_from_lengths: Dict[str, int],
) -> None:
    """Debug: log per-requirement counted_completed, counted_ip, needs_courses, required_total, remaining_to_plan, remaining_to_complete, select_from length, line range."""
    for name, b in out.items():
        completed = b.get("completed_courses", [])
        in_progress = b.get("in_progress_courses", [])
        needs = b.get("needs_courses")
        completed_n = len(completed)
        ip_n = len(in_progress)
        required_total = (completed_n + ip_n + needs) if needs is not None else (completed_n + ip_n)
        remaining_to_plan = max(0, required_total - (completed_n + ip_n))
        remaining_to_complete = max(0, required_total - completed_n)
        sel_len = select_from_lengths.get(name, 0)
        start_end = line_indices.get(name, (None, None))
        logger.info(
            "core_requirement[%s] counted_completed=%s counted_ip=%s needs_courses=%s required_total=%s remaining_to_plan=%s remaining_to_complete=%s select_from_lines=%s line_range=%s",
            name,
            completed,
            in_progress,
            needs,
            required_total,
            remaining_to_plan,
            remaining_to_complete,
            sel_len,
            start_end,
        )


def parse_core_requirements(lines: List[str], debug: bool = False) -> Dict[str, Any]:
    """
    Parse the core section of the audit PDF with a strict core window and state machine.

    Source of truth: Audit PDF. "Counted so far" = only courses listed under each core
    heading in the audit. Catalog is for recommendations only.

    Core window:
    - Start only after line containing both "University Core Requirements" and "Morrissey".
    - Stop immediately on: Intermediate Proficiency, Major Requirements, Component (,
      Elective Courses Counting Toward Degree Credits, Courses Not Counting Toward Degree Credits.

    State machine:
    - current_requirement_name, counted_completed, counted_ip, needs, in_select_from, select_from_lines.
    - Course lines only count when: inside core window, current_requirement is set, and NOT in_select_from.
    - SELECT FROM: append lines until next requirement header or core window end (cross-page safe).
    """
    in_core_section = False
    current_requirement_name: Optional[str] = None
    current_requirement_courses_counted: List[str] = []
    current_requirement_courses_ip: List[str] = []
    current_requirement_needs: Optional[int] = None
    in_select_from = False
    select_from_lines: List[str] = []

    out: Dict[str, Any] = {}
    line_indices: Dict[str, Tuple[int, int]] = {}
    select_from_lengths: Dict[str, int] = {}
    current_block_start_line: Optional[int] = None

    def ensure_bucket(name: str) -> Dict[str, Any]:
        if name not in out:
            out[name] = {
                "completed_courses": [],
                "in_progress_courses": [],
                "needs_courses": None,
                "select_from_raw": None,
            }
        return out[name]

    def finalize_select_from(bucket_name: str) -> None:
        if not bucket_name or not select_from_lines:
            return
        b = ensure_bucket(bucket_name)
        text = " ".join(select_from_lines).strip()
        if text:
            b["select_from_raw"] = text
        select_from_lengths[bucket_name] = len(select_from_lines)

    def commit_current_requirement() -> None:
        """Flush current requirement state into out and reset (except name when we switch)."""
        if not current_requirement_name:
            return
        b = ensure_bucket(current_requirement_name)
        b["completed_courses"] = list(current_requirement_courses_counted)
        b["in_progress_courses"] = list(current_requirement_courses_ip)
        b["needs_courses"] = current_requirement_needs
        if current_block_start_line is not None:
            line_indices[current_requirement_name] = (current_block_start_line, -1)

    def start_requirement(name: str, line_idx: int) -> None:
        nonlocal current_requirement_name, current_requirement_courses_counted
        nonlocal current_requirement_courses_ip, current_requirement_needs, current_block_start_line
        commit_current_requirement()
        current_requirement_name = name
        current_requirement_courses_counted = []
        current_requirement_courses_ip = []
        current_requirement_needs = None
        current_block_start_line = line_idx
        ensure_bucket(name)

    for line_idx, raw in enumerate(lines):
        line = (raw or "").strip()
        if not line:
            continue
        if "My Audit - Audit Results Tab" in line:
            continue

        if not in_core_section:
            if _is_core_section_start(line):
                in_core_section = True
            continue

        # Core window end: stop immediately
        if _is_core_section_end(line):
            finalize_select_from(current_requirement_name)
            commit_current_requirement()
            if current_requirement_name and current_block_start_line is not None:
                line_indices[current_requirement_name] = (
                    line_indices.get(current_requirement_name, (current_block_start_line,))[0],
                    line_idx,
                )
            break

        # Next requirement header (whitelist): finalize SELECT FROM, switch requirement
        header = _match_bucket_heading(line)
        if header is not None:
            finalize_select_from(current_requirement_name)
            start_requirement(header, line_idx)
            in_select_from = False
            select_from_lines = []
            continue

        if current_requirement_name is None:
            continue

        b = ensure_bucket(current_requirement_name)

        # NEEDS: N COURSE(S) only
        needs = _parse_needs_courses(line)
        if needs is not None:
            current_requirement_needs = needs
            b["needs_courses"] = needs
            continue

        # SELECT FROM: enter block; append until next requirement header or core window end
        if "SELECT FROM" in line.upper():
            in_select_from = True
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            select_from_lines = [after] if after else []
            continue

        if in_select_from:
            select_from_lines.append(line)
            continue

        # Course line: only add when inside core window, requirement set, and NOT in_select_from (guardrail)
        m = TRANSCRIPT_LINE_RE.match(line)
        if m:
            course_code = _normalize_course_code(m.group("course"))
            grade_token = (m.group("grade") or "").upper()
            status, _ = _classify_grade(grade_token)
            if status == "in_progress":
                current_requirement_courses_ip.append(course_code)
            elif status == "withdrawn":
                pass  # W → do not count
            else:
                current_requirement_courses_counted.append(course_code)
            continue

    finalize_select_from(current_requirement_name)
    commit_current_requirement()

    result = _normalize_core_output(out, line_indices)
    if debug:
        _log_core_debug(out, line_indices, select_from_lengths)
    return result


def parse_audit_pdf(pdf_path: str, debug: bool = False) -> Dict[str, Any]:
    """
    Parse audit PDF and return TWO outputs:
      A) transcript_courses: attempted courses (term-coded line only)
      B) core_requirements: core bucket status from audit (source of truth)
    If debug=True, log per-requirement state to logger.
    """
    text = _extract_pdf_text(pdf_path)
    lines = text.splitlines()

    transcript_courses = parse_transcript_courses(lines)
    core_requirements = parse_core_requirements(lines, debug=debug)

    return {
        "transcript_courses": transcript_courses,
        "core_requirements": core_requirements,
    }
