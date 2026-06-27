# PLX PharmaLearnX Training Platform

Secure Python-only Flask training platform for pharmaceutical courses.

## Features
- Home, About, Courses, Instructor Profile, Photo Gallery, Contact pages
- Admin and student login/logout
- Admin/student password change
- Editable logo path and website settings
- bKash, Nagad, bank/card payment details editable by admin
- WhatsApp and Zoom link support
- Course category with specific Other field
- Course module add/edit/delete
- Paid-only course material access
- Student enrollment and payment submission
- Admin payment approval and Google Drive access management
- Quiz, Kahoot link, certificate generation and verification
- Attractive admin/student dashboard
- Security: CSRF, security headers, failed login limit, strong password rule

## Render
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn wsgi:application

Set environment variables in Render, not in GitHub:
SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, SESSION_COOKIE_SECURE, ENABLE_HSTS
