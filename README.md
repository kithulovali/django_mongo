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
```
DJANGO_SECRET_KEY=change-me
DEBUG=1
ALLOWED_HOSTS=*
MONGODB_URI=mongodb://localhost:27017/kfc_db
MONGODB_NAME=kfc_db
GEMINI_API_KEY=your_gemini_key
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
6. Visit:
- http://127.0.0.1:8000/ for customer
- http://127.0.0.1:8000/admin/ for Django admin auth
- http://127.0.0.1:8000/kfc-admin/dashboard/ for custom admin

## Notes
- Product images use GridFS via MongoEngine `FileField`. Upload in custom admin.
- If Gemini key is missing, the app returns friendly fallbacks.
