PLX PharmaLearnX Python-Only LMS
================================

No Java. No JavaScript.
All application logic is Python Flask. UI is rendered from Python template strings.

Designed for no-domain/no-server commercial workflow:
1. Upload PDF/video to Google Drive.
2. Keep Google Drive folder restricted.
3. Add Drive folder/module link in this software.
4. Student registers with Gmail ID.
5. Student enrolls in course.
6. Student pays by bKash/Nagad/Card record.
7. Admin approves payment.
8. Admin shares Google Drive folder with student's Gmail.
9. Admin marks Drive access as given.
10. Student completes quiz and gets certificate.
Admin login credentials will be set securely in the hosting environment.
Default/admin password must not be stored in GitHub.






How to run:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py



Important:
This local Python app is your admin management system. Without hosting/server, students cannot access it from their own devices unless you run it on a shared network or deploy it later. Commercially, use Google Drive access sharing + manual payment approval.


LOCAL COMMERCIAL WORKFLOW VERSION
--------------------------------
This version is optimized for no-domain/no-server commercial use:
- Google Form registration/payment data can be manually added.
- Admin Panel includes Add Student Manually.
- Admin Panel includes Manual Enrollment.
- Admin Panel includes Manual Payment Record.
- Workflow Guide page is included.
- Google Form fields and Google Drive folder structure templates are included.

Use:
1. Run START_WINDOWS_FIXED.bat
2. Login as admin
3. Open Workflow Guide
4. Use Admin Panel for manual student/payment/enrollment record
5. Use Drive Access Manager to track Google Drive access


SECURE ONLINE DEPLOY VERSION
----------------------------
This package is prepared for online hosting with security hardening.

Added security:
- CSRF protection for POST forms
- Security headers
- Debug mode off
- Login failed attempt rate limiting
- Strong password requirement for new student registration
- Change Password page
- Secure cookie option for HTTPS hosting
- Database backup route for admin
- Render deployment files
- PythonAnywhere deployment guide
- Environment variable example

Important for online hosting:
1. Change default admin password immediately.
2. Set SECRET_KEY in hosting environment.
3. Use HTTPS.
4. Set SESSION_COOKIE_SECURE=true.
5. Keep Google Drive folders restricted.
6. Download regular database backups.
