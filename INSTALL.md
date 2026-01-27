# Installation Instructions

## Current Status

Django is not currently installed. You need to install dependencies first.

## Quick Start (When Network is Available)

### Option 1: Use the start script
```bash
cd /Users/jasonjung/Downloads/Projects/degreeplanner
./start_server.sh
```

### Option 2: Manual installation
```bash
cd /Users/jasonjung/Downloads/Projects/degreeplanner

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (if needed)
python3 -c "from django.core.management.utils import get_random_secret_key; print('SECRET_KEY=' + get_random_secret_key())" > .env
echo "DEBUG=True" >> .env
echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> .env

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start server
python manage.py runserver
```

Then open http://localhost:8000 in your browser.

## If You Have Network Issues

The installation requires internet connectivity to download packages from PyPI. If you're offline:

1. Wait for network connectivity
2. Or install packages manually from downloaded wheels
3. Or use a system Python that already has Django installed

## Required Packages

- Django>=5.0.0
- django-allauth>=0.57.0
- PyYAML>=6.0.1
- python-dotenv>=1.0.0
- Pillow>=10.0.0
- pypdf>=6.6.2

Once installed, the server will start and you can access the web interface at http://localhost:8000
