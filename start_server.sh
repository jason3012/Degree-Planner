#!/bin/bash
# Start script for Degree Planner

cd "$(dirname "$0")"

echo "Setting up Degree Planner..."

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    python3 -c "from django.core.management.utils import get_random_secret_key; print('SECRET_KEY=' + get_random_secret_key())" > .env
    echo "DEBUG=True" >> .env
    echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> .env
fi

# Run migrations
echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if needed (skip if exists)
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print("Creating superuser...")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("Superuser created: admin/admin")
else:
    print("Superuser already exists")
EOF

# Start server
echo "Starting Django development server..."
echo "Open http://localhost:8000 in your browser"
python manage.py runserver
