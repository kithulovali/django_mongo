# KFC Ordering System

Django + MongoEngine (MongoDB) food ordering system with Google Gemini AI.

## Features
- Customer menu, cart, checkout, order history, receipts
- Admin dashboard, products (GridFS images), orders, analytics via Gemini
- Bootstrap 5, KFC-themed

## Setup
1. Python 3.10+
2. Create virtualenv and install deps:
```
pip install -r requirements.txt
```
3. Environment variables (e.g. in .env):
request for these details
```
DJANGO_SECRET_KEY=
DEBUG=
ALLOWED_HOSTS=
MONGODB_URI=mongodb:
MONGODB_NAME=
GEMINI_API_KEY=
```
4. Run Django migrations (for auth/sessions only) and superuser:
```
python manage.py migrate
python manage.py createsuperuser
```
5. Run server:
```
python manage.py runserver
```

## Notes
- Product images use GridFS via MongoEngine `FileField`. Upload in custom admin.
- If Gemini key is missing, the app returns friendly fallbacks.
