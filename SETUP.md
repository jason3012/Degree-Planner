# Quick Setup Guide

## 1. Install Dependencies

```bash
cd /Users/jasonjung/Downloads/Projects/degreeplanner
source venv/bin/activate  # or: . venv/bin/activate
pip install -r requirements.txt
```

## 2. Create .env File

```bash
cat > .env << EOF
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
GEMINI_API_KEY=your-key-here
EOF
```

## 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## 4. Import Your Catalog CSV

```bash
python manage.py import_catalog /Users/jasonjung/Downloads/Projects/webscraper/core_courses_dataset.csv --semester "Spring 2026" --current
```

## 5. Run Server

```bash
python manage.py runserver
```

Visit http://localhost:8000

## Next Steps

1. Set up Google OAuth in Google Cloud Console
2. Add Google credentials to .env
3. Upload a degree audit PDF
4. View core status and available sections

See README.md for full documentation.
