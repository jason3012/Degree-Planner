# Degree Planner

- Django 5.0+ project setup with custom user model
- Database models for Semester, Course, Section, Audit, AuditCourse, and CoreTag (Section.core_tags M2M)
- Catalog import management command for CSV course data; parses core tags column and attaches CoreTag to sections (authoritative eligible-by-core)
- PDF degree audit parser: transcript courses; core section parsed with strict window (University Core … Morrissey → stop at Intermediate Proficiency / Major / Component / Electives)
- Core requirement status from audit only: counted_completed, counted_in_progress, needs_courses (NEEDS: N COURSE(S)); required_total, remaining_to_plan, remaining_to_complete; status complete / in_progress / incomplete (SELECT FROM kept for debug only)
- Eligible Spring sections from CSV: Section.filter(semester, core_tags__name=mapped_tag); fuzzy-match audit headings to CoreTag names (difflib, threshold 0.65)
- Core status page: “Counted so far”, “In progress”, “Remaining to plan” / “Remaining to complete”; eligible sections when remaining_to_plan > 0 or “show eligible anyway” toggle; optional core debug panel (?debug=1)
- YAML-based requirements engine (ALL_OF, ANY_OF, N_OF) still used for offered-sections flow where needed
- CSV export for core status (remaining_to_plan / remaining_to_complete)
- Google Sheets export structure (requires OAuth setup)
- AI assistant using Gemini API with grounded recommendations
- User authentication with Django Allauth and Google OAuth
- UI templates for landing, dashboard, audit upload, core status, sections, and AI chat
- Google-only login flow (Get Started → Google OAuth)

**Note:** Core requirement status was updated to fix misattribution (e.g. Cultural Diversity swallowing transcript/major content). Audit drives “what counts so far”; catalog CSV drives “eligible sections”. Cultural diversity behavior may still need further tuning.
