#!/usr/bin/env python
"""
Setup Google OAuth SocialApp for django-allauth from environment variables.
Run this after setting GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv('GOOGLE_CLIENT_ID', '')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')

if not client_id or not client_secret:
    print("ERROR: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env file")
    print("\nTo set up Google OAuth:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable Google+ API")
    print("4. Go to Credentials -> Create Credentials -> OAuth 2.0 Client ID")
    print("5. Set Application type to 'Web application'")
    print("6. Add authorized redirect URI: http://localhost:8000/accounts/google/login/callback/")
    print("7. Copy Client ID and Client Secret to your .env file:")
    print("   GOOGLE_CLIENT_ID=your-client-id-here")
    print("   GOOGLE_CLIENT_SECRET=your-client-secret-here")
    exit(1)

# Get or create the site
site = Site.objects.get(id=1)

# Get or create the Google SocialApp
google_app, created = SocialApp.objects.get_or_create(
    provider='google',
    defaults={
        'name': 'Google',
        'client_id': client_id,
        'secret': client_secret,
    }
)

if not created:
    # Update existing app
    google_app.client_id = client_id
    google_app.secret = client_secret
    google_app.save()
    print("Updated existing Google SocialApp")
else:
    print("Created new Google SocialApp")

# Add site to the app
if site not in google_app.sites.all():
    google_app.sites.add(site)
    print(f"Added site '{site.domain}' to Google SocialApp")
else:
    print(f"Site '{site.domain}' already associated with Google SocialApp")

print("\n✅ Google OAuth is now configured!")
print(f"   Client ID: {client_id[:20]}...")
print(f"   Site: {site.domain}")
