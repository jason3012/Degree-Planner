# Project Location

The Degree Planner Django project is located at:

**`/Users/jasonjung/Downloads/Projects/degreeplanner/`**

## Project Structure

```
degreeplanner/
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── README.md             # Full documentation
├── SETUP.md              # Quick setup guide
├── start_server.sh       # Server startup script
│
├── app/                  # Main Django application
│   ├── settings.py       # Django settings
│   ├── urls.py          # URL routing
│   ├── users/           # User authentication
│   ├── catalog/         # Course catalog models
│   ├── audits/          # Degree audit parsing
│   ├── planner/         # Core planning views
│   ├── exports/         # CSV/Sheets export
│   ├── assistant/       # AI assistant
│   ├── rules/           # Requirements engine
│   └── templates/      # HTML templates
│
├── requirements/        # YAML requirement files
│   ├── core_v1.yaml
│   └── equivalencies.yaml
│
└── catalog_import/      # Import utilities
```

## Related Project

The webscraper project (which created the CSV) is at:
**`/Users/jasonjung/Downloads/Projects/webscraper/`**

You can import the CSV from webscraper into degreeplanner using:
```bash
python manage.py import_catalog ../webscraper/core_courses_dataset.csv --semester "Spring 2026" --current
```
