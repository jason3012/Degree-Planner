"""
Core requirement utilities: map audit headings to CSV/DB core tag names.
"""
import re
from difflib import SequenceMatcher
from typing import Optional, Set

# Minimum ratio to accept a match (e.g. "Theology: PULSE..." -> "Theology")
FUZZY_MATCH_THRESHOLD = 0.65


def _normalize_heading(text: str) -> str:
    """Lowercase, remove punctuation, collapse spaces."""
    if not text:
        return ""
    s = re.sub(r"[^\w\s]", "", (text or "").lower())
    return " ".join(s.split())


def map_audit_heading_to_core_tag(audit_heading: str, canonical_names: Set[str]) -> str:
    """
    Fuzzy-match audit heading to a canonical CoreTag name from DB.
    Returns best match if score >= threshold, else returns raw heading (for "unknown").
    """
    if not audit_heading or not canonical_names:
        return audit_heading or ""
    normalized = _normalize_heading(audit_heading)
    if not normalized:
        return audit_heading
    best_name: Optional[str] = None
    best_ratio = 0.0
    for name in canonical_names:
        canon_norm = _normalize_heading(name)
        if not canon_norm:
            continue
        ratio = SequenceMatcher(None, normalized, canon_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_name = name
    if best_ratio >= FUZZY_MATCH_THRESHOLD and best_name:
        return best_name
    return audit_heading
