# Degree Planner

- Django 5.0+ project setup with custom user model
- Database models for Semester, Course, Section, Audit, and AuditCourse
- Catalog import management command for CSV course data
- PDF degree audit parser that extracts courses, credits, and status
- YAML-based requirements engine supporting ALL_OF, ANY_OF, N_OF, and LEAF nodes
- Core requirement evaluation and status tracking
- Section matching for remaining requirements with day/time filtering
- CSV export for core status and available sections
- Google Sheets export structure (requires OAuth setup)
- AI assistant using Gemini API with grounded recommendations
- User authentication with Django Allauth and Google OAuth
- UI templates for landing, dashboard, audit upload, core status, sections, and AI chat
