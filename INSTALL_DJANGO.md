# Installing Django - Network Issue Detected

## Current Problem

Your system cannot reach PyPI (Python Package Index) due to a network connectivity issue. The error "nodename nor servname provided, or not known" indicates DNS resolution is failing.

## Solutions

### Option 1: Fix Network Connectivity (Recommended)

1. **Check your internet connection**
   - Ensure you're connected to the internet
   - Try: `ping google.com` to test connectivity

2. **Check DNS settings**
   - Your DNS might not be resolving hostnames
   - Try: `nslookup pypi.org` to test DNS

3. **Try installing again once network is working:**
   ```bash
   cd /Users/jasonjung/Downloads/Projects/degreeplanner
   source venv/bin/activate
   pip install Django django-allauth PyYAML python-dotenv Pillow pypdf
   ```

### Option 2: Manual Installation (If you have Django wheel file)

If you have a Django wheel file (.whl) downloaded:
```bash
cd /Users/jasonjung/Downloads/Projects/degreeplanner
source venv/bin/activate
pip install /path/to/Django-*.whl
```

### Option 3: Use System Python (If Django is installed there)

If Django is installed in your system Python:
```bash
cd /Users/jasonjung/Downloads/Projects/degreeplanner
# Use system Python instead of venv
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 manage.py runserver
```

### Option 4: Download Django Manually

1. Download Django from: https://pypi.org/project/Django/#files
2. Download as a wheel file (.whl)
3. Install locally:
   ```bash
   pip install /path/to/downloaded/Django-*.whl
   ```

## Once Django is Installed

After Django is successfully installed, run:

```bash
cd /Users/jasonjung/Downloads/Projects/degreeplanner
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Then open http://localhost:8000 in your browser.

## Quick Test

To test if network is working:
```bash
curl https://pypi.org
ping google.com
nslookup pypi.org
```

If these fail, you have a network/DNS issue that needs to be resolved first.
