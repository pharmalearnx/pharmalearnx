import re
from __future__ import annotations

import csv
import io
import os
import sqlite3
import secrets
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, request, redirect, url_for, session, flash, render_template_string, Response, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "plx_local_commercial.sqlite3"
ASSET_DIR = BASE_DIR / "static" / "assets"
DB_PATH.parent.mkdir(exist_ok=True)
ASSET_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_urlsafe(48))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


STYLE = """
:root{--primary:#0c4dff;--accent:#ff8a00;--ink:#0f172a;--muted:#64748b;--line:#dde5f0;--bg:#f3f7ff;--white:#fff;--danger:#b91c1c;--success:#047857;--warning:#b45309;--radius:22px;--shadow:0 18px 45px rgba(15,23,42,.10);--grad:linear-gradient(135deg,#0c4dff,#12b8d6,#ff8a00)}
*{box-sizing:border-box}body{margin:0;font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:var(--bg)}a{text-decoration:none;color:inherit}button,input,select,textarea{font:inherit}button{cursor:pointer}.layout{display:grid;grid-template-columns:300px 1fr;min-height:100vh}.sidebar{background:radial-gradient(circle at top right,rgba(18,184,214,.24),transparent 28%),linear-gradient(180deg,#0a1630,#12284f);color:#fff;padding:24px;position:sticky;top:0;height:100vh;overflow:auto;display:flex;flex-direction:column;gap:18px}.brand{display:flex;gap:14px;align-items:center;border-bottom:1px solid rgba(255,255,255,.12);padding-bottom:16px}.logo-box{width:72px;height:72px;border-radius:22px;background:#fff;display:grid;place-items:center;overflow:hidden}.logo-box img{width:100%;height:100%;object-fit:contain}.brand strong{display:block;font-size:26px}.brand small{display:block;color:#d5def0;font-weight:700}.brand em{display:block;color:rgba(255,255,255,.72);font-style:normal;font-size:11px;margin-top:4px}nav{display:flex;flex-direction:column;gap:8px}nav a,.userbox button{border:0;border-radius:14px;padding:12px 13px;color:#d7e2f4;background:transparent;font-weight:800;text-align:left}nav a:hover{background:linear-gradient(90deg,rgba(12,77,255,.28),rgba(18,184,214,.18));color:#fff}.userbox{margin-top:auto;border-top:1px solid rgba(255,255,255,.12);padding-top:14px}.userbox button{border:1px solid rgba(255,255,255,.22);width:100%;text-align:center}.topbar{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.88);border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;padding:22px 32px}.topbar p{margin:0;background:var(--grad);-webkit-background-clip:text;color:transparent;font-weight:900;letter-spacing:1px;text-transform:uppercase;font-size:12px}.topbar h1{margin:4px 0 0;font-size:25px}.badge{background:linear-gradient(135deg,rgba(12,77,255,.08),rgba(17,197,190,.10));border:1px solid rgba(12,77,255,.12);border-radius:999px;padding:9px 14px;font-weight:900}.content{padding:32px}.card,.stat,.auth-card,.course-card,.certificate,.table-wrap{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}.card,.auth-card{padding:24px}.auth-card{max-width:580px;margin:30px auto}.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.mt{margin-top:18px}.stat{padding:24px;position:relative;overflow:hidden}.stat:before{content:"";position:absolute;inset:0 0 auto 0;height:4px;background:var(--grad)}.stat span{color:var(--muted);font-weight:800}.stat strong{display:block;font-size:34px;color:var(--primary);margin-top:5px}.page-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:18px}.page-head h2{margin:0;font-size:22px}.course-card{padding:24px;display:flex;flex-direction:column;min-height:300px}.course-card h3{font-size:18px}.tag{display:inline-flex;width:max-content;border-radius:999px;padding:6px 10px;background:linear-gradient(135deg,rgba(12,77,255,.12),rgba(17,197,190,.10));font-weight:900;font-size:12px}.meta{display:flex;gap:8px;flex-wrap:wrap;margin:auto 0 14px}.meta span{background:#f1f5f9;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:800}.primary,.secondary,.danger,.button{border:0;border-radius:999px;min-height:40px;padding:9px 16px;font-weight:900;display:inline-flex;align-items:center;justify-content:center}.primary{background:var(--grad);color:#fff}.secondary{background:#fff;color:var(--primary);border:1px solid var(--line)}.danger{background:#fee2e2;color:var(--danger)}.small{min-height:32px;padding:6px 11px;font-size:13px}label{display:block;font-weight:900;color:#334155;margin:13px 0}input,select,textarea{width:100%;min-height:44px;border:1px solid var(--line);border-radius:13px;padding:10px 12px;margin-top:7px;background:#fff}textarea{resize:vertical}.notice{background:#f8fafc;border:1px solid var(--line);border-radius:15px;padding:13px;line-height:1.6}.notice.warning,.flash.warning{background:#fffbeb;border-color:#fde68a;color:#92400e}.notice.success,.flash.success{background:#ecfdf5;border-color:#99f6e4;color:var(--success)}.flash.danger,.notice.danger{background:#fef2f2;border-color:#fecaca;color:var(--danger)}.flash{padding:13px;margin-bottom:18px;font-weight:800;border-radius:15px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:#fff}th,td{text-align:left;padding:13px;border-bottom:1px solid var(--line);vertical-align:top}th{background:#f1f5f9;color:#475569;text-transform:uppercase;font-size:12px}.inline{display:inline}.chips{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}.chips a,.chip{display:inline-flex;padding:8px 12px;border-radius:999px;background:linear-gradient(135deg,rgba(12,77,255,.08),rgba(17,197,190,.08));border:1px solid rgba(12,77,255,.14);font-weight:800}.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.step{padding:14px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(135deg,rgba(12,77,255,.05),rgba(255,138,0,.05))}.step b{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:var(--grad);color:#fff}.step span{display:block;font-weight:900;margin-top:8px}.step small{color:var(--muted)}.resource-card,.question{border:1px solid var(--line);border-radius:16px;padding:16px;margin:14px 0}.option{font-weight:700}.option input{width:auto;min-height:auto}.certificate{text-align:center;border:7px solid #e6eefb;padding:30px;background:linear-gradient(180deg,#fff,#f8fbff);position:relative;overflow:hidden}.certificate.premium:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:var(--grad)}.certificate.classic{border-color:#d4af37;background:#fffdf7}.seal{width:64px;height:64px;margin:0 auto 10px;border-radius:50%;display:grid;place-items:center;background:var(--grad);color:#fff;font-weight:900}.cert-name{font-size:28px;font-weight:900}.cert-course{font-size:18px;font-weight:900}.cert-id{font-weight:900;color:var(--muted)}.copybox{font-family:monospace;white-space:pre-wrap;background:#0f172a;color:#e2e8f0;border-radius:16px;padding:16px;line-height:1.6}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media print{body *{visibility:hidden}.certificate,.certificate *{visibility:visible}.certificate{position:absolute;left:0;top:0;width:100%;box-shadow:none}.no-print,.sidebar,.topbar{display:none!important}}@media(max-width:1100px){.layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.grid4,.grid3,.grid2{grid-template-columns:1fr}}
"""

BASE = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ setting('short_name') }} | {{ setting('full_name') }}</title><style>{{ style }}</style></head><body>
<div class="layout">
<aside class="sidebar">
<div class="brand"><div class="logo-box"><img src="{{ url_for('static', filename=setting('logo_path')) }}" alt="PLX"></div><div><strong>{{ setting('short_name') }}</strong><small>{{ setting('full_name') }}</small><em>{{ setting('tagline') }}</em></div></div>
{% if current_user %}
<nav>
<a href="{{ url_for('dashboard') }}">Dashboard</a><a href="{{ url_for('workflow_guide') }}">Workflow Guide</a><a href="{{ url_for('courses') }}">Courses</a><a href="{{ url_for('payments') }}">Payments</a><a href="{{ url_for('learning') }}">My Learning</a><a href="{{ url_for('quiz') }}">Quiz</a><a href="{{ url_for('certificates') }}">Certificates</a><a href="{{ url_for('verify') }}">Verify Certificate</a>
{% if is_admin %}<a href="{{ url_for('drive_access') }}">Drive Access Manager</a><a href="{{ url_for('materials') }}">Training Module Links</a><a href="{{ url_for('admin_panel') }}">Admin Panel</a><a href="{{ url_for('categories') }}">Categories</a><a href="{{ url_for('quiz_manager') }}">Quiz Manager</a><a href="{{ url_for('student_export') }}">Export Students</a><a href="{{ url_for('audit_view') }}">Audit Trail</a>{% endif %}
<a href="{{ url_for('change_password') }}">Change Password</a>{% if is_admin %}<a href="{{ url_for('security_check') }}">Security Check</a><a href="{{ url_for('backup_database') }}">Backup Database</a>{% endif %}<a href="{{ url_for('settings') }}">Settings</a>
</nav><div class="userbox"><p>{{ current_user.name }}<br><small>{{ current_user.email }} • {{ current_user.role }}</small></p><form method="post" action="{{ url_for('logout') }}"><button>Logout</button></form></div>
{% else %}
<nav><a href="{{ url_for('public_home') }}">Public Training Page</a><a href="{{ url_for('login') }}">Login</a><a href="{{ url_for('register') }}">Student Register</a><a href="{{ url_for('verify') }}">Verify Certificate</a></nav>
{% endif %}
</aside>
<main><header class="topbar"><div><p>{{ setting('short_name') }} | {{ setting('academy_name') }}</p><h1>{{ title }}</h1></div><span class="badge">{{ current_user.role|upper if current_user else 'GUEST' }}</span></header>
<section class="content">{% for category,message in get_flashed_messages(with_categories=true) %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{{ body|safe }}</section>
</main></div></body></html>
"""

FAILED_LOGINS = {}
MAX_FAILED_LOGINS = int(os.environ.get("MAX_FAILED_LOGINS", "5"))
LOGIN_BLOCK_SECONDS = int(os.environ.get("LOGIN_BLOCK_SECONDS", "900"))

def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token

def inject_csrf(body: str) -> str:
    token_field = f'<input type="hidden" name="_csrf_token" value="{csrf_token()}">'
    body = body.replace('<form method="post"', '<form method="post"')
    body = re.sub(r'(<form\b[^>]*method=["\']post["\'][^>]*>)', r'\1' + token_field, body, flags=re.I)
    return body

@app.before_request
def csrf_protect():
    if request.method == "POST":
        form_token = request.form.get("_csrf_token", "")
        session_token = session.get("_csrf_token", "")
        if not form_token or not session_token or not secrets.compare_digest(form_token, session_token):
            abort(400)

@app.after_request
def add_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    if os.environ.get("ENABLE_HSTS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

def is_rate_limited(email: str, ip: str):
    key = f"{email}|{ip}"
    record = FAILED_LOGINS.get(key)
    if not record:
        return False
    count, first_time = record
    if time.time() - first_time > LOGIN_BLOCK_SECONDS:
        FAILED_LOGINS.pop(key, None)
        return False
    return count >= MAX_FAILED_LOGINS

def record_failed_login(email: str, ip: str):
    key = f"{email}|{ip}"
    count, first_time = FAILED_LOGINS.get(key, (0, time.time()))
    FAILED_LOGINS[key] = (count + 1, first_time)

def clear_failed_login(email: str, ip: str):
    FAILED_LOGINS.pop(f"{email}|{ip}", None)

def strong_password(password: str) -> tuple[bool, str]:
    if len(password) < 10:
        return False, "Password must be at least 10 characters."
    if not any(ch.isupper() for ch in password):
        return False, "Password must include at least one uppercase letter."
    if not any(ch.islower() for ch in password):
        return False, "Password must include at least one lowercase letter."
    if not any(ch.isdigit() for ch in password):
        return False, "Password must include at least one number."
    if not any(ch in "!@#$%^&*()-_=+[]{};:,.?/|" for ch in password):
        return False, "Password must include at least one special character."
    return True, ""

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def q_all(sql, args=()):
    with db() as con:
        return con.execute(sql, args).fetchall()

def q_one(sql, args=()):
    with db() as con:
        return con.execute(sql, args).fetchone()

def execute(sql, args=()):
    with db() as con:
        cur = con.execute(sql, args)
        con.commit()
        return int(cur.lastrowid or 0)

def setting(key, default=""):
    row = q_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default

def set_setting(key, value):
    execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def money(value):
    try:
        return "৳" + f"{float(value):,.0f}"
    except Exception:
        return "৳0"


def make_student_password(phone: str = "") -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return digits[-6:] if len(digits) >= 6 else "student123"

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return q_one("SELECT * FROM users WHERE id=? AND active=1", (uid,))

def is_admin():
    u = current_user()
    return bool(u and u["role"] == "admin")

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_admin():
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper

def audit(action, details=""):
    u = current_user()
    execute("INSERT INTO audit_trail(at_time,actor_id,actor_name,actor_role,action,details) VALUES(?,?,?,?,?,?)",
            (now(), u["id"] if u else None, u["name"] if u else "System", u["role"] if u else "system", action, details))

def render_page(title, body, **ctx):
    body = inject_csrf(body)
    return render_template_string(BASE, title=title, body=body, style=STYLE, current_user=current_user(), is_admin=is_admin(), setting=setting, money=money, csrf_token=csrf_token, **ctx)

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,gmail TEXT,phone TEXT,company TEXT,designation TEXT,password_hash TEXT,role TEXT,active INTEGER DEFAULT 1,created_at TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT,title TEXT,category TEXT,duration TEXT,fee REAL,description TEXT,drive_folder_link TEXT,active INTEGER DEFAULT 1,created_at TEXT);
        CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,course_id INTEGER,status TEXT,drive_access_status TEXT DEFAULT 'not_given',access_note TEXT DEFAULT '',score INTEGER,enrolled_at TEXT,completed_at TEXT,UNIQUE(user_id,course_id));
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,enrollment_id INTEGER,user_id INTEGER,course_id INTEGER,method TEXT,amount REAL,wallet_number TEXT,trx_id TEXT,status TEXT DEFAULT 'submitted',submitted_at TEXT,reviewed_at TEXT,note TEXT);
        CREATE TABLE IF NOT EXISTS resources(id INTEGER PRIMARY KEY AUTOINCREMENT,course_id INTEGER,type TEXT,title TEXT,drive_link TEXT,active INTEGER DEFAULT 1,created_at TEXT);
        CREATE TABLE IF NOT EXISTS quizzes(id INTEGER PRIMARY KEY AUTOINCREMENT,course_id INTEGER,question TEXT,option1 TEXT,option2 TEXT,option3 TEXT,option4 TEXT,answer INTEGER);
        CREATE TABLE IF NOT EXISTS kahoot_links(course_id INTEGER PRIMARY KEY,link TEXT);
        CREATE TABLE IF NOT EXISTS certificates(id INTEGER PRIMARY KEY AUTOINCREMENT,certificate_code TEXT UNIQUE,user_id INTEGER,course_id INTEGER,score INTEGER,issued_at TEXT);
        CREATE TABLE IF NOT EXISTS audit_trail(id INTEGER PRIMARY KEY AUTOINCREMENT,at_time TEXT,actor_id INTEGER,actor_name TEXT,actor_role TEXT,action TEXT,details TEXT);
        """)
        con.commit()

    defaults = {
        "short_name":"PLX","academy_name":"PharmaLearnX","full_name":"PharmaLearnX LMS",
        "tagline":"Pharmaceutical Learning Excellence","email":"Pharmalearnx@gmail.com",
        "phone":"01618881616","bkash_number":"01618881616","nagad_number":"01618881616",
        "google_drive_email":"Pharmalearnx@gmail.com","certificate_title":"Certificate of Training Completion",
        "certificate_footer":"Pharmaceutical Learning Excellence","certificate_template":"premium","logo_path":"assets/plx_logo.png",
    }
    for k,v in defaults.items():
        execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k,v))

    if not q_one("SELECT id FROM users WHERE email=?", ("admin@pharmalearnx.com",)):
        execute("INSERT INTO users(name,email,gmail,phone,password_hash,role,active,created_at) VALUES(?,?,?,?,?,?,1,?)",
                (os.environ.get("ADMIN_NAME","PLX Administrator"), os.environ.get("ADMIN_EMAIL","admin@pharmalearnx.com"), os.environ.get("ADMIN_EMAIL","admin@pharmalearnx.com"), "01618881616", generate_password_hash(os.environ.get("ADMIN_PASSWORD","ChangeMe@12345!")), "admin", now()))
    if not q_all("SELECT id FROM categories"):
        for c in ["GMP","QA","QC","Regulatory Affairs","Validation","Audit","Production","Others"]:
            execute("INSERT INTO categories(name) VALUES(?)", (c,))
    if not q_all("SELECT id FROM courses"):
        courses=[("GMP-101","Basic GMP for Pharmaceutical Industry","GMP","2 hours",1000,"GMP principles, documentation and compliance culture."),
                 ("GDP-102","Good Documentation Practice & Data Integrity","GMP","3 hours",1500,"ALCOA+, error correction, audit trail and record review."),
                 ("QA-201","Deviation, CAPA & Root Cause Analysis","QA","4 hours",2000,"Deviation handling, 5-Why, fishbone and CAPA effectiveness."),
                 ("RA-401","CTD Module 3 & Dossier Preparation","Regulatory Affairs","5 hours",3000,"Drug substance/product, specification, validation and stability basics.")]
        for c in courses:
            execute("INSERT INTO courses(code,title,category,duration,fee,description,drive_folder_link,active,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (*c,"",1,now()))
    if not q_all("SELECT id FROM quizzes"):
        first=q_one("SELECT id FROM courses ORDER BY id LIMIT 1")
        if first:
            for q in [("What does GMP mainly ensure?","Consistent quality standard","Only marketing","Only speed","Only color",1),
                      ("Which one is part of ALCOA?","Attributable","Adjustable","Artificial","Avoidable",1),
                      ("Main purpose of CAPA is:","Prevent recurrence","Hide deviation","Delete record","Increase batch",1)]:
                execute("INSERT INTO quizzes(course_id,question,option1,option2,option3,option4,answer) VALUES(?,?,?,?,?,?,?)",(first["id"],*q))

@app.route("/public")
def public_home():
    courses=q_all("SELECT * FROM courses WHERE active=1 ORDER BY id DESC")
    body=render_template_string("""
    <div class="card"><h2>{{ setting('academy_name') }} Training Platform</h2>
    <p class="notice">No server/domain model: student payment korbe bKash/Nagad e, Gmail ID submit korbe, admin payment verify kore Google Drive folder access debe.</p>
    <div class="chips"><a>bKash: {{ setting('bkash_number') }}</a><a>Nagad: {{ setting('nagad_number') }}</a><a>Drive Gmail: {{ setting('google_drive_email') }}</a></div></div>
    <div class="grid3 mt">{% for c in courses %}<div class="course-card"><span class="tag">{{ c.code }}</span><h3>{{ c.title }}</h3><p>{{ c.description }}</p><div class="meta"><span>{{ c.category }}</span><span>{{ c.duration }}</span><span>{{ money(c.fee) }}</span></div><a class="button primary" href="{{ url_for('register') }}">Register</a></div>{% endfor %}</div>
    """, courses=courses, setting=setting, money=money)
    return render_page("Public Training Page", body)

@app.route("/login", methods=["GET","POST"])
def login():
    if current_user(): 
        return redirect(url_for("dashboard"))
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        pw=request.form.get("password","")
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
        if is_rate_limited(email, ip):
            flash("Too many failed login attempts. Please try again later.", "danger")
            return redirect(url_for("login"))
        u=q_one("SELECT * FROM users WHERE email=? AND active=1",(email,))
        if u and check_password_hash(u["password_hash"],pw):
            session.clear()
            session["user_id"]=u["id"]
            csrf_token()
            clear_failed_login(email, ip)
            audit("USER_LOGIN",email)
            flash("Login successful.","success")
            return redirect(url_for("dashboard"))
        record_failed_login(email, ip)
        flash("Invalid login.","danger")
    body="""<div class="auth-card"><h2>Sign in</h2><p class="notice warning"><b>Security Note:</b> For online hosting, change the default admin password immediately after first login.</p><form method="post"><label>Email <input name="email" type="email" required></label><label>Password <input name="password" type="password" required></label><button class="primary">Login</button> <a class="button secondary" href="{{ url_for('register') }}">Student Register</a></form></div>"""
    return render_page("Login", render_template_string(body))


@app.route("/register", methods=["GET","POST"])
def register():
    if current_user(): return redirect(url_for("dashboard"))
    if request.method=="POST":
        data={k:request.form.get(k,"").strip() for k in ["name","email","gmail","phone","company","designation"]}
        pw=request.form.get("password","")
        ok, msg = strong_password(pw)
        if not data["name"] or not data["email"] or not ok:
            flash("Name, email and strong password required. " + msg, "danger"); return redirect(url_for("register"))
        try:
            uid=execute("INSERT INTO users(name,email,gmail,phone,company,designation,password_hash,role,active,created_at) VALUES(?,?,?,?,?,?,?,?,1,?)",
                        (data["name"],data["email"].lower(),data["gmail"],data["phone"],data["company"],data["designation"],generate_password_hash(pw),"student",now()))
            session["user_id"]=uid; audit("STUDENT_REGISTERED",data["email"]); flash("Registration successful.","success"); return redirect(url_for("courses"))
        except sqlite3.IntegrityError:
            flash("Email already registered.","danger")
    body="""<div class="auth-card"><h2>Student Registration</h2><form method="post"><label>Full Name <input name="name" required></label><label>Email <input name="email" type="email" required></label><label>Gmail for Google Drive Access <input name="gmail" placeholder="example@gmail.com"></label><label>Phone <input name="phone"></label><label>Company <input name="company"></label><label>Designation <input name="designation"></label><label>Password <input name="password" type="password" minlength="6" required></label><button class="primary">Register</button></form></div>"""
    return render_page("Student Registration", body)

@app.post("/logout")
def logout():
    audit("USER_LOGOUT"); session.clear(); flash("Logged out.","success"); return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    u=current_user()
    if is_admin():
        enroll=q_all("SELECT * FROM enrollments"); cert=q_all("SELECT * FROM certificates"); pending=q_all("SELECT * FROM payments WHERE status='submitted'"); access=q_all("SELECT * FROM enrollments WHERE status IN ('paid','completed') AND drive_access_status!='given'")
    else:
        enroll=q_all("SELECT * FROM enrollments WHERE user_id=?",(u["id"],)); cert=q_all("SELECT * FROM certificates WHERE user_id=?",(u["id"],)); pending=q_all("SELECT * FROM payments WHERE user_id=? AND status='submitted'",(u["id"],)); access=[]
    body=render_template_string("""
    <div class="grid4"><div class="stat"><span>Enrollments</span><strong>{{ enroll|length }}</strong></div><div class="stat"><span>Certificates</span><strong>{{ cert|length }}</strong></div><div class="stat"><span>Payment Pending</span><strong>{{ pending|length }}</strong></div><div class="stat"><span>Drive Access Pending</span><strong>{{ access|length }}</strong></div></div>
    <div class="grid2 mt"><div class="card"><h2>Commercial Training Workflow</h2><div class="steps">{% for n,t,d in steps %}<div class="step"><b>{{ n }}</b><span>{{ t }}</span><small>{{ d }}</small></div>{% endfor %}</div></div>
    <div class="card"><h2>No Server / No Domain Model</h2><p class="notice">Ei app local admin panel. Student payment kore, admin verify kore Google Drive access debe.</p><div class="chips"><a>bKash: {{ setting('bkash_number') }}</a><a>Nagad: {{ setting('nagad_number') }}</a><a>Gmail: {{ setting('google_drive_email') }}</a></div></div></div>
    """, enroll=enroll, cert=cert, pending=pending, access=access, setting=setting, steps=[("1","Register","Student + Gmail"),("2","Enroll","Select course"),("3","Payment","bKash/Nagad/Card"),("4","Approve","Admin verify"),("5","Drive Access","Share folder"),("6","Learning","PDF/video links"),("7","Quiz/Certificate","Complete and issue")])
    return render_page("Dashboard", body)

@app.route("/courses")
@login_required
def courses():
    selected=request.args.get("category","All")
    cats=q_all("SELECT * FROM categories ORDER BY name")
    courses=q_all("SELECT * FROM courses WHERE active=1 ORDER BY id DESC") if selected=="All" else q_all("SELECT * FROM courses WHERE active=1 AND category=? ORDER BY id DESC",(selected,))
    enrollments={e["course_id"]:e for e in q_all("SELECT * FROM enrollments WHERE user_id=?",(current_user()["id"],))}
    body=render_template_string("""
    <div class="page-head"><div><h2>Available Courses</h2><p>Select course and submit payment.</p></div><form><select name="category" onchange="this.form.submit()"><option value="All">All Categories</option>{% for c in cats %}<option value="{{ c.name }}" {{ 'selected' if selected==c.name else '' }}>{{ c.name }}</option>{% endfor %}</select></form></div>
    <div class="grid3">{% for c in courses %}<div class="course-card"><span class="tag">{{ c.code }}</span><h3>{{ c.title }}</h3><p>{{ c.description }}</p><div class="meta"><span>{{ c.category }}</span><span>{{ c.duration }}</span><span>{{ money(c.fee) }}</span></div>{% if is_admin %}<a class="button secondary" href="{{ url_for('edit_course', course_id=c.id) }}">Edit</a>{% elif enrollments.get(c.id) %}<button class="secondary" disabled>{{ enrollments.get(c.id).status.replace('_',' ') }}</button>{% else %}<form method="post" action="{{ url_for('enroll', course_id=c.id) }}"><button class="primary">Enroll & Pay</button></form>{% endif %}</div>{% endfor %}</div>
    """, cats=cats, selected=selected, courses=courses, enrollments=enrollments, money=money, is_admin=is_admin())
    return render_page("Courses", body)

@app.post("/enroll/<int:course_id>")
@login_required
def enroll(course_id):
    if is_admin():
        flash("Admin cannot enroll.","warning"); return redirect(url_for("courses"))
    course=q_one("SELECT * FROM courses WHERE id=? AND active=1",(course_id,))
    if not course: abort(404)
    try:
        execute("INSERT INTO enrollments(user_id,course_id,status,enrolled_at) VALUES(?,?,?,?)",(current_user()["id"],course_id,"pending_payment",now()))
        audit("COURSE_ENROLLED",course["title"]); flash("Course enrolled. Submit payment.","success"); return redirect(url_for("payments"))
    except sqlite3.IntegrityError:
        flash("Already enrolled.","warning"); return redirect(url_for("courses"))

@app.route("/payments", methods=["GET","POST"])
@login_required
def payments():
    u=current_user()
    if request.method=="POST" and not is_admin():
        eid=int(request.form.get("enrollment_id","0") or 0)
        method=request.form.get("method","")
        wallet=request.form.get("wallet_number","").strip()
        trx=request.form.get("trx_id","").strip()
        enr=q_one("SELECT * FROM enrollments WHERE id=? AND user_id=?",(eid,u["id"]))
        if not enr: flash("Enrollment not found.","danger"); return redirect(url_for("payments"))
        c=q_one("SELECT * FROM courses WHERE id=?",(enr["course_id"],))
        if method in ("bkash","nagad") and (not wallet or not trx):
            flash("Wallet number and Transaction ID required.","danger"); return redirect(url_for("payments"))
        execute("INSERT INTO payments(enrollment_id,user_id,course_id,method,amount,wallet_number,trx_id,status,submitted_at) VALUES(?,?,?,?,?,?,?,?,?)",(eid,u["id"],enr["course_id"],method,c["fee"],wallet,trx,"submitted",now()))
        execute("UPDATE enrollments SET status='payment_submitted' WHERE id=?",(eid,))
        audit("PAYMENT_SUBMITTED",method); flash("Payment submitted for admin approval.","success"); return redirect(url_for("payments"))

    if is_admin():
        status=request.args.get("status","submitted")
        rows=q_all("""SELECT p.*,u.name user_name,u.email user_email,u.gmail user_gmail,c.title course_title FROM payments p JOIN users u ON u.id=p.user_id JOIN courses c ON c.id=p.course_id """ + ("" if status=="all" else "WHERE p.status=? ") + "ORDER BY p.id DESC", () if status=="all" else (status,))
        body=render_template_string("""
        <div class="card"><div class="page-head"><div><h2>Payment Verification</h2><p>Dropdown diye payment status edit korun.</p></div><form><select name="status" onchange="this.form.submit()">{% for st in ['submitted','approved','rejected','all'] %}<option value="{{ st }}" {{ 'selected' if status==st else '' }}>{{ st }}</option>{% endfor %}</select></form></div>
        {% if rows %}<div class="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Method</th><th>Info</th><th>Amount</th><th>Status</th><th>Update</th></tr></thead><tbody>{% for p in rows %}<tr><td>{{ p.user_name }}<br><small>{{ p.user_email }}<br>Drive: {{ p.user_gmail }}</small></td><td>{{ p.course_title }}</td><td>{{ p.method }}</td><td>Wallet: {{ p.wallet_number }}<br>TrxID: {{ p.trx_id }}</td><td>{{ money(p.amount) }}</td><td>{{ p.status }}</td><td><form method="post" action="{{ url_for('payment_review', payment_id=p.id) }}"><select name="status"><option>submitted</option><option>approved</option><option>rejected</option></select><button class="primary small">Save</button></form></td></tr>{% endfor %}</tbody></table></div>{% else %}<p class="notice success">No payment found.</p>{% endif %}</div>
        """, rows=rows, status=status, money=money)
        return render_page("Payment Verification", body)

    payable=q_all("""SELECT e.*,c.title course_title,c.fee FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=? AND e.status IN ('pending_payment','payment_rejected')""",(u["id"],))
    history=q_all("""SELECT p.*,c.title course_title FROM payments p JOIN courses c ON c.id=p.course_id WHERE p.user_id=? ORDER BY p.id DESC""",(u["id"],))
    body=render_template_string("""
    <div class="grid2"><div class="card"><h2>Submit Payment</h2><div class="chips"><a>bKash: {{ setting('bkash_number') }}</a><a>Nagad: {{ setting('nagad_number') }}</a></div>{% if payable %}<form method="post"><label>Select Course <select name="enrollment_id">{% for e in payable %}<option value="{{ e.id }}">{{ e.course_title }} - {{ money(e.fee) }}</option>{% endfor %}</select></label><label>Method <select name="method"><option value="bkash">bKash</option><option value="nagad">Nagad</option><option value="card">Card/Bank Record</option></select></label><label>Wallet/Card Reference <input name="wallet_number"></label><label>Transaction ID <input name="trx_id"></label><button class="primary">Submit Payment</button></form>{% else %}<p class="notice success">No pending payment.</p>{% endif %}</div>
    <div class="card"><h2>My Payment History</h2>{% if history %}<div class="table-wrap"><table><thead><tr><th>Course</th><th>Method</th><th>Amount</th><th>Status</th></tr></thead><tbody>{% for p in history %}<tr><td>{{ p.course_title }}</td><td>{{ p.method }}</td><td>{{ money(p.amount) }}</td><td>{{ p.status }}</td></tr>{% endfor %}</tbody></table></div>{% else %}<p class="notice">No payment record.</p>{% endif %}</div></div>
    """, payable=payable, history=history, setting=setting, money=money)
    return render_page("Payment System", body)

@app.post("/payments/<int:payment_id>/review")
@admin_required
def payment_review(payment_id):
    status=request.form.get("status","submitted")
    p=q_one("SELECT * FROM payments WHERE id=?",(payment_id,))
    if not p: abort(404)
    execute("UPDATE payments SET status=?,reviewed_at=? WHERE id=?",(status,now(),payment_id))
    estatus="paid" if status=="approved" else "payment_rejected" if status=="rejected" else "payment_submitted"
    execute("UPDATE enrollments SET status=? WHERE id=?",(estatus,p["enrollment_id"]))
    audit("PAYMENT_"+status.upper(),str(payment_id)); flash("Payment status updated.","success"); return redirect(url_for("payments"))

@app.route("/drive-access", methods=["GET","POST"])
@admin_required
def drive_access():
    if request.method=="POST":
        execute("UPDATE enrollments SET drive_access_status=?,access_note=? WHERE id=?",(request.form.get("drive_access_status"),request.form.get("access_note",""),int(request.form.get("enrollment_id"))))
        audit("DRIVE_ACCESS_UPDATED",request.form.get("drive_access_status")); flash("Drive access updated.","success"); return redirect(url_for("drive_access"))
    rows=q_all("""SELECT e.*,u.name user_name,u.email user_email,u.gmail user_gmail,c.title course_title,c.drive_folder_link FROM enrollments e JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id WHERE e.status IN ('paid','completed') ORDER BY e.id DESC""")
    body=render_template_string("""
    <div class="card"><h2>Google Drive Access Manager</h2><p class="notice">Payment approve howar por student Gmail ID ke Google Drive folder-e Viewer access din. Tarpor ekhane 'given' kore save korun.</p>{% if rows %}<div class="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Drive Folder</th><th>Status</th><th>Message</th><th>Update</th></tr></thead><tbody>{% for r in rows %}<tr><td>{{ r.user_name }}<br><small>{{ r.user_email }}<br>Gmail: {{ r.user_gmail }}</small></td><td>{{ r.course_title }}</td><td>{% if r.drive_folder_link %}<a target="_blank" href="{{ r.drive_folder_link }}">Open Folder</a>{% else %}No link{% endif %}</td><td>{{ r.drive_access_status }}</td><td><div class="copybox">Dear {{ r.user_name }},\nYour payment has been approved for {{ r.course_title }}.\nGoogle Drive access has been shared to: {{ r.user_gmail }}.\nRegards,\n{{ setting('academy_name') }}</div></td><td><form method="post"><input type="hidden" name="enrollment_id" value="{{ r.id }}"><select name="drive_access_status"><option>not_given</option><option>given</option><option>removed</option></select><input name="access_note" value="{{ r.access_note }}" placeholder="Note"><button class="primary small">Save</button></form></td></tr>{% endfor %}</tbody></table></div>{% else %}<p class="notice warning">No approved enrollment found.</p>{% endif %}</div>
    """, rows=rows, setting=setting)
    return render_page("Drive Access Manager", body)

@app.route("/materials", methods=["GET","POST"])
@admin_required
def materials():
    if request.method=="POST":
        course_id=int(request.form.get("course_id"))
        title=request.form.get("title","").strip()
        link=request.form.get("drive_link","").strip()
        if not title or not link.startswith(("http://","https://")):
            flash("Title and valid Google Drive link required.","danger"); return redirect(url_for("materials"))
        execute("INSERT INTO resources(course_id,type,title,drive_link,active,created_at) VALUES(?,?,?,?,1,?)",(course_id,request.form.get("type"),title,link,now()))
        audit("RESOURCE_LINK_ADDED",title); flash("Training module link saved.","success"); return redirect(url_for("materials"))
    courses=q_all("SELECT * FROM courses ORDER BY title")
    resources=q_all("SELECT r.*,c.title course_title FROM resources r JOIN courses c ON c.id=r.course_id WHERE r.active=1 ORDER BY r.id DESC")
    body=render_template_string("""
    <div class="grid2"><div class="card"><h2>Add Training Module Link</h2><p class="notice">PDF/video Google Drive-e upload kore link ekhane add korun.</p><form method="post"><label>Course <select name="course_id">{% for c in courses %}<option value="{{ c.id }}">{{ c.title }}</option>{% endfor %}</select></label><label>Type <select name="type"><option value="pdf">PDF Material</option><option value="video">Video Class</option><option value="drive_folder">Drive Folder</option><option value="other">Other</option></select></label><label>Title <input name="title" required></label><label>Google Drive Link <input name="drive_link" required></label><button class="primary">Save Module</button></form></div>
    <div class="card"><h2>Saved Training Modules</h2>{% for r in resources %}<div class="resource-card"><span class="tag">{{ r.type }}</span><h3>{{ r.title }}</h3><p>{{ r.course_title }}</p><a class="button primary small" target="_blank" href="{{ r.drive_link }}">Open</a><form method="post" action="{{ url_for('delete_resource', resource_id=r.id) }}" class="inline"><button class="danger small">Delete</button></form></div>{% else %}<p class="notice warning">No module added yet.</p>{% endfor %}</div></div>
    """, courses=courses, resources=resources)
    return render_page("Training Module Links", body)

@app.post("/resources/<int:resource_id>/delete")
@admin_required
def delete_resource(resource_id):
    execute("UPDATE resources SET active=0 WHERE id=?",(resource_id,)); flash("Resource removed.","success"); return redirect(url_for("materials"))

@app.route("/learning")
@login_required
def learning():
    if is_admin():
        rows=q_all("SELECT id course_id,title,drive_folder_link,'given' drive_access_status FROM courses ORDER BY id DESC")
    else:
        rows=q_all("""SELECT e.course_id,e.drive_access_status,c.title,c.drive_folder_link FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=? AND e.status IN ('paid','completed')""",(current_user()["id"],))
    resource_map={r["course_id"]:q_all("SELECT * FROM resources WHERE course_id=? AND active=1 ORDER BY id DESC",(r["course_id"],)) for r in rows}
    body=render_template_string("""
    <p class="notice">Google Drive support email: <strong>{{ setting('google_drive_email') }}</strong></p>{% if rows %}{% for row in rows %}<div class="card mt"><h2>{{ row.title }}</h2>{% if row.drive_access_status!='given' %}<p class="notice warning">Payment approved, but Drive access may still be pending.</p>{% endif %}{% if row.drive_folder_link %}<p><a class="button primary" target="_blank" href="{{ row.drive_folder_link }}">Open Course Drive Folder</a></p>{% endif %}{% for r in resource_map[row.course_id] %}<div class="resource-card"><span class="tag">{{ r.type }}</span><h3>{{ r.title }}</h3><a class="button primary" target="_blank" href="{{ r.drive_link }}">Open Module</a></div>{% else %}<p class="notice">No PDF/video module link added yet.</p>{% endfor %}</div>{% endfor %}{% else %}<p class="notice warning">No accessible course found. Payment approval required.</p>{% endif %}
    """, rows=rows, resource_map=resource_map, setting=setting)
    return render_page("My Learning", body)

@app.route("/quiz", methods=["GET","POST"])
@login_required
def quiz():
    if is_admin(): return redirect(url_for("quiz_manager"))
    eligible=q_all("SELECT e.*,c.title course_title FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=? AND e.status='paid'",(current_user()["id"],))
    cid=int(request.values.get("course_id") or (eligible[0]["course_id"] if eligible else 0))
    questions=q_all("SELECT * FROM quizzes WHERE course_id=?",(cid,)) if cid else []
    kahoot=q_one("SELECT * FROM kahoot_links WHERE course_id=?",(cid,)) if cid else None
    if request.method=="POST" and request.form.get("submit_quiz"):
        if not questions: flash("No manual quiz available.","warning"); return redirect(url_for("quiz"))
        score=sum(1 for q in questions if request.form.get(f"q_{q['id']}") and int(request.form.get(f"q_{q['id']}"))==q["answer"])
        pct=round(score/len(questions)*100)
        if pct<70: flash(f"Not passed. Score: {pct}%.","danger"); return redirect(url_for("quiz",course_id=cid))
        execute("UPDATE enrollments SET status='completed',score=?,completed_at=? WHERE user_id=? AND course_id=?",(pct,now(),current_user()["id"],cid))
        if not q_one("SELECT id FROM certificates WHERE user_id=? AND course_id=?",(current_user()["id"],cid)):
            code=f"PLX-{datetime.now().year}-{len(q_all('SELECT id FROM certificates'))+1:04d}"
            execute("INSERT INTO certificates(certificate_code,user_id,course_id,score,issued_at) VALUES(?,?,?,?,?)",(code,current_user()["id"],cid,pct,now()))
        flash(f"Passed. Score: {pct}%. Certificate generated.","success"); return redirect(url_for("certificates"))
    body=render_template_string("""
    <div class="card">{% if eligible %}<form><label>Select Paid Course <select name="course_id" onchange="this.form.submit()">{% for e in eligible %}<option value="{{ e.course_id }}" {{ 'selected' if cid==e.course_id else '' }}>{{ e.course_title }}</option>{% endfor %}</select></label></form>{% if kahoot %}<p class="notice success">Kahoot: <a target="_blank" href="{{ kahoot.link }}">Open Kahoot Quiz</a></p>{% endif %}{% if questions %}<form method="post"><input type="hidden" name="course_id" value="{{ cid }}">{% for q in questions %}<div class="question"><h3>{{ loop.index }}. {{ q.question }}</h3>{% for n,opt in [(1,q.option1),(2,q.option2),(3,q.option3),(4,q.option4)] %}<label class="option"><input type="radio" name="q_{{ q.id }}" value="{{ n }}" required> {{ opt }}</label>{% endfor %}</div>{% endfor %}<button class="primary" name="submit_quiz" value="1">Submit Manual Quiz</button></form>{% else %}<p class="notice warning">No manual quiz found.</p>{% endif %}{% else %}<p class="notice warning">No paid course available for quiz.</p>{% endif %}</div>
    """, eligible=eligible, cid=cid, questions=questions, kahoot=kahoot)
    return render_page("Quiz", body)

@app.route("/quiz-manager", methods=["GET","POST"])
@admin_required
def quiz_manager():
    courses=q_all("SELECT * FROM courses ORDER BY title")
    cid=int(request.values.get("course_id") or (courses[0]["id"] if courses else 0))
    if request.method=="POST":
        action=request.form.get("action")
        if action=="kahoot":
            execute("INSERT INTO kahoot_links(course_id,link) VALUES(?,?) ON CONFLICT(course_id) DO UPDATE SET link=excluded.link",(cid,request.form.get("kahoot_link","").strip()))
            flash("Kahoot link saved.","success")
        else:
            qid=request.form.get("quiz_id")
            vals=(cid,request.form.get("question",""),request.form.get("option1",""),request.form.get("option2",""),request.form.get("option3",""),request.form.get("option4",""),int(request.form.get("answer","1")))
            if qid: execute("UPDATE quizzes SET course_id=?,question=?,option1=?,option2=?,option3=?,option4=?,answer=? WHERE id=?",(*vals,int(qid)))
            else: execute("INSERT INTO quizzes(course_id,question,option1,option2,option3,option4,answer) VALUES(?,?,?,?,?,?,?)",vals)
            flash("Quiz saved.","success")
        return redirect(url_for("quiz_manager",course_id=cid))
    qs=q_all("SELECT * FROM quizzes WHERE course_id=? ORDER BY id DESC",(cid,))
    kahoot=q_one("SELECT * FROM kahoot_links WHERE course_id=?",(cid,))
    body=render_template_string("""
    <div class="grid2"><div class="card"><h2>Kahoot & Manual Quiz Setup</h2><form><label>Select Course <select name="course_id" onchange="this.form.submit()">{% for c in courses %}<option value="{{ c.id }}" {{ 'selected' if cid==c.id else '' }}>{{ c.title }}</option>{% endfor %}</select></label></form><form method="post" class="resource-card"><input type="hidden" name="course_id" value="{{ cid }}"><input type="hidden" name="action" value="kahoot"><label>Kahoot Link <input name="kahoot_link" value="{{ kahoot.link if kahoot else '' }}"></label><button class="primary">Save Kahoot</button></form><form method="post" class="resource-card"><input type="hidden" name="action" value="quiz"><label>Question <input name="question" required></label><label>Option 1 <input name="option1" required></label><label>Option 2 <input name="option2" required></label><label>Option 3 <input name="option3" required></label><label>Option 4 <input name="option4" required></label><label>Correct <select name="answer"><option value="1">Option 1</option><option value="2">Option 2</option><option value="3">Option 3</option><option value="4">Option 4</option></select></label><button class="primary">Add Quiz</button></form></div>
    <div class="card"><h2>Current Quiz List</h2>{% for q in qs %}<div class="resource-card"><h3>{{ q.question }}</h3><p>1. {{ q.option1 }}<br>2. {{ q.option2 }}<br>3. {{ q.option3 }}<br>4. {{ q.option4 }}</p><p><b>Correct:</b> Option {{ q.answer }}</p><form method="post"><input type="hidden" name="action" value="quiz"><input type="hidden" name="quiz_id" value="{{ q.id }}"><input name="question" value="{{ q.question }}"><input name="option1" value="{{ q.option1 }}"><input name="option2" value="{{ q.option2 }}"><input name="option3" value="{{ q.option3 }}"><input name="option4" value="{{ q.option4 }}"><select name="answer">{% for n in [1,2,3,4] %}<option value="{{ n }}" {{ 'selected' if q.answer==n else '' }}>Option {{ n }}</option>{% endfor %}</select><button class="secondary small">Edit</button></form><form method="post" action="{{ url_for('delete_quiz', quiz_id=q.id) }}"><button class="danger small">Delete</button></form></div>{% else %}<p class="notice warning">No question added.</p>{% endfor %}</div></div>
    """, courses=courses, cid=cid, qs=qs, kahoot=kahoot)
    return render_page("Quiz Manager", body)

@app.post("/quiz-manager/<int:quiz_id>/delete")
@admin_required
def delete_quiz(quiz_id):
    r=q_one("SELECT * FROM quizzes WHERE id=?",(quiz_id,))
    cid=r["course_id"] if r else 0
    execute("DELETE FROM quizzes WHERE id=?",(quiz_id,))
    flash("Quiz deleted.","success"); return redirect(url_for("quiz_manager",course_id=cid))

def cert_html(cert):
    return render_template_string("""<div class="certificate {{ setting('certificate_template') }}"><div class="seal">{{ setting('short_name') }}</div><h2>{{ setting('certificate_title') }}</h2><p>This is to certify that</p><div class="cert-name">{{ cert.user_name }}</div><p>has successfully completed the training on</p><div class="cert-course">{{ cert.course_title }}</div><p>Score: {{ cert.score }}% • Issued: {{ cert.issued_at }}</p><p class="cert-id">Certificate ID: {{ cert.certificate_code }}</p><p>{{ setting('certificate_footer') }}</p><button onclick="window.print()" class="secondary no-print">Print</button></div>""", cert=cert, setting=setting)

@app.route("/certificates")
@login_required
def certificates():
    rows=q_all("""SELECT cert.*,u.name user_name,c.title course_title FROM certificates cert JOIN users u ON u.id=cert.user_id JOIN courses c ON c.id=cert.course_id """ + ("" if is_admin() else "WHERE cert.user_id=? ") + "ORDER BY cert.id DESC", () if is_admin() else (current_user()["id"],))
    body=render_template_string("""<div class="grid2">{% for cert in rows %}{{ cert_html(cert)|safe }}{% else %}<p class="notice warning">No certificate found.</p>{% endfor %}</div>""", rows=rows, cert_html=cert_html)
    return render_page("Certificates", body)

@app.route("/verify")
def verify():
    code=request.args.get("certificate_code","").strip()
    cert=q_one("""SELECT cert.*,u.name user_name,c.title course_title FROM certificates cert JOIN users u ON u.id=cert.user_id JOIN courses c ON c.id=cert.course_id WHERE cert.certificate_code=?""",(code,)) if code else None
    body=render_template_string("""<div class="card"><h2>Certificate Verification</h2><form><label>Certificate ID <input name="certificate_code" value="{{ code }}" placeholder="PLX-2026-0001"></label><button class="primary">Verify</button></form></div>{% if code %}{% if cert %}<div class="flash success mt">Certificate verified successfully.</div>{{ cert_html(cert)|safe }}{% else %}<div class="flash danger mt">Certificate not found.</div>{% endif %}{% endif %}""", code=code, cert=cert, cert_html=cert_html)
    return render_page("Verify Certificate", body)

@app.route("/admin", methods=["GET","POST"])
@admin_required
def admin_panel():
    if request.method=="POST":
        action=request.form.get("action")

        if action=="course":
            cat=request.form.get("custom_category","").strip() or request.form.get("category","Others")
            if not q_one("SELECT id FROM categories WHERE name=?",(cat,)):
                execute("INSERT INTO categories(name) VALUES(?)",(cat,))
            execute(
                "INSERT INTO courses(code,title,category,duration,fee,description,drive_folder_link,active,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    request.form.get("code","").strip(),
                    request.form.get("title","").strip(),
                    cat,
                    request.form.get("duration","").strip(),
                    float(request.form.get("fee") or 0),
                    request.form.get("description","").strip(),
                    request.form.get("drive_folder_link","").strip(),
                    1,
                    now()
                )
            )
            audit("COURSE_CREATED", request.form.get("title",""))
            flash("Course added.", "success")

        elif action=="admin":
            try:
                execute(
                    "INSERT INTO users(name,email,gmail,phone,password_hash,role,active,created_at) VALUES(?,?,?,?,?,?,1,?)",
                    (
                        request.form.get("name","").strip(),
                        request.form.get("email","").strip().lower(),
                        request.form.get("email","").strip().lower(),
                        "",
                        generate_password_hash(request.form.get("password","")),
                        "admin",
                        now()
                    )
                )
                audit("ADMIN_CREATED", request.form.get("email",""))
                flash("Admin created.", "success")
            except sqlite3.IntegrityError:
                flash("Email already exists.", "danger")

        elif action=="student":
            name=request.form.get("student_name","").strip()
            email=request.form.get("student_email","").strip().lower()
            gmail=request.form.get("student_gmail","").strip()
            phone=request.form.get("student_phone","").strip()
            company=request.form.get("student_company","").strip()
            designation=request.form.get("student_designation","").strip()
            password=request.form.get("student_password","").strip() or make_student_password(phone)
            if not name or not email:
                flash("Student name and email are required.", "danger")
            else:
                try:
                    execute(
                        "INSERT INTO users(name,email,gmail,phone,company,designation,password_hash,role,active,created_at) VALUES(?,?,?,?,?,?,?,?,1,?)",
                        (name,email,gmail,phone,company,designation,generate_password_hash(password),"student",now())
                    )
                    audit("STUDENT_MANUALLY_ADDED", email)
                    flash(f"Student added. Temporary password: {password}", "success")
                except sqlite3.IntegrityError:
                    flash("Student email already exists.", "danger")

        elif action=="manual_enroll":
            user_id=int(request.form.get("manual_user_id","0") or 0)
            course_id=int(request.form.get("manual_course_id","0") or 0)
            status=request.form.get("manual_status","pending_payment")
            if user_id and course_id:
                try:
                    execute(
                        "INSERT INTO enrollments(user_id,course_id,status,enrolled_at) VALUES(?,?,?,?)",
                        (user_id,course_id,status,now())
                    )
                    audit("MANUAL_ENROLLMENT_CREATED", f"user={user_id}, course={course_id}, status={status}")
                    flash("Manual enrollment added.", "success")
                except sqlite3.IntegrityError:
                    execute("UPDATE enrollments SET status=? WHERE user_id=? AND course_id=?", (status,user_id,course_id))
                    audit("MANUAL_ENROLLMENT_UPDATED", f"user={user_id}, course={course_id}, status={status}")
                    flash("Enrollment already existed; status updated.", "success")

        elif action=="manual_payment":
            enrollment_id=int(request.form.get("manual_enrollment_id","0") or 0)
            method=request.form.get("manual_payment_method","bkash")
            trx=request.form.get("manual_trx_id","").strip()
            wallet=request.form.get("manual_wallet","").strip()
            status=request.form.get("manual_payment_status","approved")
            enr=q_one("SELECT e.*, c.fee FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.id=?", (enrollment_id,))
            if not enr:
                flash("Enrollment not found for payment record.", "danger")
            else:
                execute(
                    "INSERT INTO payments(enrollment_id,user_id,course_id,method,amount,wallet_number,trx_id,status,submitted_at,reviewed_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (enrollment_id,enr["user_id"],enr["course_id"],method,enr["fee"],wallet,trx,status,now(),now())
                )
                enroll_status="paid" if status=="approved" else "payment_rejected" if status=="rejected" else "payment_submitted"
                execute("UPDATE enrollments SET status=? WHERE id=?", (enroll_status,enrollment_id))
                audit("MANUAL_PAYMENT_RECORDED", f"enrollment={enrollment_id}, method={method}, status={status}")
                flash("Manual payment record saved.", "success")

        return redirect(url_for("admin_panel"))

    courses=q_all("SELECT * FROM courses ORDER BY id DESC")
    users=q_all("SELECT * FROM users ORDER BY id DESC")
    students=q_all("SELECT * FROM users WHERE role='student' ORDER BY id DESC")
    cats=q_all("SELECT * FROM categories ORDER BY name")
    enrollments=q_all("""SELECT e.*, u.name user_name, u.email user_email, c.title course_title 
                         FROM enrollments e JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id 
                         ORDER BY e.id DESC""")
    body=render_template_string("""
    <div class="card">
      <h2>Local Commercial Workflow</h2>
      <p class="notice success">
        Ei panel Google Form + Google Drive + bKash/Nagad manual commercial model-er jonno.
        Student jodi Google Form submit kore, apni ekhane manually student add, enroll, payment record and Drive access track korte parben.
      </p>
    </div>

    <div class="grid2 mt">
      <div class="card">
        <h2>Add Student Manually</h2>
        <p class="notice">Google Form theke পাওয়া student information ekhane add korun.</p>
        <form method="post">
          <input type="hidden" name="action" value="student">
          <label>Student Name <input name="student_name" required></label>
          <label>Email <input name="student_email" type="email" required></label>
          <label>Gmail for Drive Access <input name="student_gmail" placeholder="example@gmail.com"></label>
          <label>Phone <input name="student_phone"></label>
          <label>Company <input name="student_company"></label>
          <label>Designation <input name="student_designation"></label>
          <label>Temporary Password <input name="student_password" placeholder="Blank rakhle phone-er last 6 digit"></label>
          <button class="primary">Add Student</button>
        </form>
      </div>

      <div class="card">
        <h2>Manual Enrollment</h2>
        <p class="notice">Student payment/registration form receive করার পর course enrollment record করুন.</p>
        <form method="post">
          <input type="hidden" name="action" value="manual_enroll">
          <label>Student
            <select name="manual_user_id">{% for s in students %}<option value="{{ s.id }}">{{ s.name }} - {{ s.email }}</option>{% endfor %}</select>
          </label>
          <label>Course
            <select name="manual_course_id">{% for c in courses %}<option value="{{ c.id }}">{{ c.title }}</option>{% endfor %}</select>
          </label>
          <label>Enrollment Status
            <select name="manual_status"><option value="pending_payment">pending_payment</option><option value="payment_submitted">payment_submitted</option><option value="paid">paid</option><option value="completed">completed</option></select>
          </label>
          <button class="primary">Save Enrollment</button>
        </form>
      </div>
    </div>

    <div class="grid2 mt">
      <div class="card">
        <h2>Manual Payment Record</h2>
        <p class="notice">bKash/Nagad/Card payment verify kore ekhane record রাখুন.</p>
        <form method="post">
          <input type="hidden" name="action" value="manual_payment">
          <label>Enrollment
            <select name="manual_enrollment_id">{% for e in enrollments %}<option value="{{ e.id }}">{{ e.user_name }} - {{ e.course_title }} - {{ e.status }}</option>{% endfor %}</select>
          </label>
          <label>Payment Method
            <select name="manual_payment_method"><option value="bkash">bKash</option><option value="nagad">Nagad</option><option value="card">Card/Bank Record</option></select>
          </label>
          <label>Wallet / Reference Number <input name="manual_wallet"></label>
          <label>Transaction ID <input name="manual_trx_id"></label>
          <label>Payment Status
            <select name="manual_payment_status"><option value="approved">approved</option><option value="submitted">submitted</option><option value="rejected">rejected</option></select>
          </label>
          <button class="primary">Save Payment</button>
        </form>
      </div>

      <div class="card">
        <h2>Create Admin</h2>
        <form method="post">
          <input type="hidden" name="action" value="admin">
          <label>Name <input name="name" required></label>
          <label>Email <input name="email" type="email" required></label>
          <label>Password <input name="password" required></label>
          <button class="primary">Create Admin</button>
        </form>
      </div>
    </div>

    <div class="card mt">
      <h2>Add Course</h2>
      <form method="post">
        <input type="hidden" name="action" value="course">
        <div class="form-grid">
          <label>Code <input name="code" required></label>
          <label>Title <input name="title" required></label>
        </div>
        <label>Category <select name="category">{% for c in cats %}<option>{{ c.name }}</option>{% endfor %}</select></label>
        <label>Or New Category <input name="custom_category"></label>
        <div class="form-grid">
          <label>Duration <input name="duration" required></label>
          <label>Fee <input name="fee" type="number" required></label>
        </div>
        <label>Drive Folder Link <input name="drive_folder_link" placeholder="https://drive.google.com/..."></label>
        <label>Description <textarea name="description" required></textarea></label>
        <button class="primary">Add Course</button>
      </form>
    </div>

    <div class="card mt">
      <h2>Course List</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Code</th><th>Title</th><th>Category</th><th>Fee</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>{% for c in courses %}
        <tr><td>{{ c.code }}</td><td>{{ c.title }}</td><td>{{ c.category }}</td><td>{{ money(c.fee) }}</td><td>{{ 'Active' if c.active else 'Inactive' }}</td>
        <td><a class="button secondary small" href="{{ url_for('edit_course', course_id=c.id) }}">Edit</a>
        <form method="post" action="{{ url_for('toggle_course', course_id=c.id) }}" class="inline"><button class="danger small">{{ 'Deactivate' if c.active else 'Activate' }}</button></form></td></tr>
        {% endfor %}</tbody>
      </table></div>
    </div>

    <div class="card mt">
      <h2>Student & User List</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Name</th><th>Email</th><th>Gmail</th><th>Phone</th><th>Role</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>{% for u in users %}
        <tr><td>{{ u.name }}</td><td>{{ u.email }}</td><td>{{ u.gmail }}</td><td>{{ u.phone }}</td><td>{{ u.role }}</td><td>{{ 'Active' if u.active else 'Inactive' }}</td><td><a class="button secondary small" href="{{ url_for('edit_user', user_id=u.id) }}">Edit</a></td></tr>
        {% endfor %}</tbody>
      </table></div>
    </div>
    """, courses=courses, users=users, students=students, cats=cats, enrollments=enrollments, money=money)
    return render_page("Admin Panel", body)


@app.route("/courses/<int:course_id>/edit", methods=["GET","POST"])
@admin_required
def edit_course(course_id):
    c=q_one("SELECT * FROM courses WHERE id=?",(course_id,))
    if not c: abort(404)
    cats=q_all("SELECT * FROM categories ORDER BY name")
    if request.method=="POST":
        cat=request.form.get("custom_category","").strip() or request.form.get("category","Others")
        if not q_one("SELECT id FROM categories WHERE name=?",(cat,)): execute("INSERT INTO categories(name) VALUES(?)",(cat,))
        execute("UPDATE courses SET code=?,title=?,category=?,duration=?,fee=?,description=?,drive_folder_link=? WHERE id=?",(request.form.get("code"),request.form.get("title"),cat,request.form.get("duration"),float(request.form.get("fee") or 0),request.form.get("description"),request.form.get("drive_folder_link",""),course_id))
        flash("Course updated.","success"); return redirect(url_for("admin_panel"))
    body=render_template_string("""<div class="card"><h2>Edit Course</h2><form method="post"><label>Code <input name="code" value="{{ c.code }}"></label><label>Title <input name="title" value="{{ c.title }}"></label><label>Category <select name="category">{% for cat in cats %}<option {{ 'selected' if cat.name==c.category else '' }}>{{ cat.name }}</option>{% endfor %}</select></label><label>Or New Category <input name="custom_category"></label><label>Duration <input name="duration" value="{{ c.duration }}"></label><label>Fee <input name="fee" type="number" value="{{ c.fee }}"></label><label>Drive Folder Link <input name="drive_folder_link" value="{{ c.drive_folder_link }}"></label><label>Description <textarea name="description">{{ c.description }}</textarea></label><button class="primary">Save</button></form></div>""", c=c, cats=cats)
    return render_page("Edit Course", body)

@app.post("/courses/<int:course_id>/toggle")
@admin_required
def toggle_course(course_id):
    c=q_one("SELECT * FROM courses WHERE id=?",(course_id,))
    if c: execute("UPDATE courses SET active=? WHERE id=?",(0 if c["active"] else 1,course_id))
    return redirect(url_for("admin_panel"))

@app.route("/users/<int:user_id>/edit", methods=["GET","POST"])
@admin_required
def edit_user(user_id):
    u=q_one("SELECT * FROM users WHERE id=?",(user_id,))
    if not u: abort(404)
    if request.method=="POST":
        execute("UPDATE users SET name=?,email=?,gmail=?,phone=?,company=?,designation=?,role=?,active=? WHERE id=?",(request.form.get("name"),request.form.get("email").lower(),request.form.get("gmail"),request.form.get("phone"),request.form.get("company"),request.form.get("designation"),request.form.get("role"),1 if request.form.get("active")=="1" else 0,user_id))
        flash("User updated.","success"); return redirect(url_for("admin_panel"))
    body=render_template_string("""<div class="card"><h2>Edit User</h2><form method="post"><label>Name <input name="name" value="{{ u.name }}"></label><label>Email <input name="email" value="{{ u.email }}"></label><label>Gmail <input name="gmail" value="{{ u.gmail }}"></label><label>Phone <input name="phone" value="{{ u.phone }}"></label><label>Company <input name="company" value="{{ u.company }}"></label><label>Designation <input name="designation" value="{{ u.designation }}"></label><label>Role <select name="role"><option {{ 'selected' if u.role=='student' else '' }}>student</option><option {{ 'selected' if u.role=='admin' else '' }}>admin</option></select></label><label>Status <select name="active"><option value="1" {{ 'selected' if u.active else '' }}>Active</option><option value="0" {{ 'selected' if not u.active else '' }}>Inactive</option></select></label><button class="primary">Save</button></form></div>""", u=u)
    return render_page("Edit User", body)

@app.route("/categories", methods=["GET","POST"])
@admin_required
def categories():
    if request.method=="POST":
        old=request.form.get("old_name","").strip(); name=request.form.get("name","").strip()
        if old:
            execute("UPDATE categories SET name=? WHERE name=?",(name,old)); execute("UPDATE courses SET category=? WHERE category=?",(name,old))
        else:
            try: execute("INSERT INTO categories(name) VALUES(?)",(name,))
            except sqlite3.IntegrityError: pass
        flash("Category saved.","success"); return redirect(url_for("categories"))
    rows=q_all("SELECT * FROM categories ORDER BY name")
    body=render_template_string("""<div class="grid2"><div class="card"><h2>Add Category</h2><form method="post"><label>Name <input name="name" required></label><button class="primary">Save</button></form></div><div class="card"><h2>Category List</h2>{% for c in rows %}<div class="resource-card"><form method="post"><input type="hidden" name="old_name" value="{{ c.name }}"><input name="name" value="{{ c.name }}"><button class="secondary small">Edit</button></form>{% if c.name!='Others' %}<form method="post" action="{{ url_for('delete_category', category_id=c.id) }}"><button class="danger small">Delete</button></form>{% endif %}</div>{% endfor %}</div></div>""", rows=rows)
    return render_page("Categories", body)

@app.post("/categories/<int:category_id>/delete")
@admin_required
def delete_category(category_id):
    cat=q_one("SELECT * FROM categories WHERE id=?",(category_id,))
    if cat and cat["name"]!="Others":
        execute("UPDATE courses SET category='Others' WHERE category=?",(cat["name"],)); execute("DELETE FROM categories WHERE id=?",(category_id,))
    return redirect(url_for("categories"))


@app.route("/change-password", methods=["GET","POST"])
@login_required
def change_password():
    u=current_user()
    if request.method=="POST":
        current=request.form.get("current_password","")
        new=request.form.get("new_password","")
        confirm=request.form.get("confirm_password","")
        if not check_password_hash(u["password_hash"], current):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))
        if new != confirm:
            flash("New password and confirm password do not match.", "danger")
            return redirect(url_for("change_password"))
        ok, msg = strong_password(new)
        if not ok:
            flash(msg, "danger")
            return redirect(url_for("change_password"))
        execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new), u["id"]))
        audit("PASSWORD_CHANGED", u["email"])
        flash("Password changed successfully.", "success")
        return redirect(url_for("dashboard"))
    body = """
    <div class="card">
      <h2>Change Password</h2>
      <p class="notice warning">Use a strong password. Do not use the default admin password online.</p>
      <form method="post">
        <label>Current Password <input type="password" name="current_password" required></label>
        <label>New Password <input type="password" name="new_password" required></label>
        <label>Confirm New Password <input type="password" name="confirm_password" required></label>
        <button class="primary">Change Password</button>
      </form>
    </div>
    """
    return render_page("Change Password", body)


@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    keys=["short_name","academy_name","full_name","tagline","email","phone","bkash_number","nagad_number","google_drive_email","certificate_title","certificate_footer","certificate_template"]
    if is_admin():
        if request.method=="POST":
            for k in keys: set_setting(k,request.form.get(k,""))
            logo=request.files.get("logo")
            if logo and logo.filename:
                filename="logo_"+secure_filename(logo.filename); logo.save(ASSET_DIR/filename); set_setting("logo_path","assets/"+filename)
            flash("Settings saved.","success"); return redirect(url_for("settings"))
        body=render_template_string("""<div class="card"><h2>Settings</h2><form method="post" enctype="multipart/form-data">{% for k in keys %}<label>{{ k.replace('_',' ').title() }} {% if k=='certificate_template' %}<select name="{{ k }}"><option value="premium" {{ 'selected' if setting(k)=='premium' else '' }}>Premium</option><option value="classic" {{ 'selected' if setting(k)=='classic' else '' }}>Classic</option></select>{% else %}<input name="{{ k }}" value="{{ setting(k) }}">{% endif %}</label>{% endfor %}<label>Logo <input type="file" name="logo" accept="image/*"></label><button class="primary">Save</button></form></div>""", keys=keys, setting=setting)
        return render_page("Settings", body)
    u=current_user()
    if request.method=="POST":
        execute("UPDATE users SET name=?,gmail=?,phone=?,company=?,designation=? WHERE id=?",(request.form.get("name"),request.form.get("gmail"),request.form.get("phone"),request.form.get("company"),request.form.get("designation"),u["id"]))
        flash("Profile updated.","success"); return redirect(url_for("settings"))
    body=render_template_string("""<div class="card"><h2>My Profile</h2><form method="post"><label>Name <input name="name" value="{{ u.name }}"></label><label>Email <input value="{{ u.email }}" disabled></label><label>Gmail <input name="gmail" value="{{ u.gmail }}"></label><label>Phone <input name="phone" value="{{ u.phone }}"></label><label>Company <input name="company" value="{{ u.company }}"></label><label>Designation <input name="designation" value="{{ u.designation }}"></label><button class="primary">Save</button></form></div>""", u=u)
    return render_page("Profile", body)

@app.route("/student-export")
@admin_required
def student_export():
    rows=q_all("""SELECT u.name,u.email,u.gmail,u.phone,u.company,u.designation,c.title course_title,e.status,e.drive_access_status FROM enrollments e JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id ORDER BY e.id DESC""")
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Name","Email","Gmail","Phone","Company","Designation","Course","Status","Drive Access"])
    for r in rows: w.writerow([r["name"],r["email"],r["gmail"],r["phone"],r["company"],r["designation"],r["course_title"],r["status"],r["drive_access_status"]])
    return Response(out.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=plx_students_drive_access.csv"})


@app.route("/workflow-guide")
@login_required
def workflow_guide():
    body = render_template_string("""
    <div class="card">
      <h2>No Server / No Domain Commercial Workflow</h2>
      <ol>
        <li>Google Drive-e course-wise restricted folder create korun.</li>
        <li>PDF/video upload korun and folder permission Restricted rakhun.</li>
        <li>Google Form diye student registration/payment data collect korun.</li>
        <li>Admin Panel → Add Student Manually.</li>
        <li>Admin Panel → Manual Enrollment.</li>
        <li>Payment verify kore Admin Panel → Manual Payment Record.</li>
        <li>Drive Access Manager → student Gmail ke Drive folder viewer access diye status = given korun.</li>
        <li>Quiz complete korle certificate issue hobe.</li>
      </ol>
    </div>

    <div class="grid2 mt">
      <div class="card">
        <h2>Google Form Fields</h2>
        <div class="copybox">Full Name
Company Name
Designation
Email
Gmail for Google Drive Access
Phone / WhatsApp
Course Name
Payment Method
Transaction ID
Payment Screenshot
Declaration: I confirm that submitted information is correct.</div>
      </div>
      <div class="card">
        <h2>Payment Instruction Text</h2>
        <div class="copybox">Please complete payment to confirm your enrollment.

bKash: {{ setting('bkash_number') }}
Nagad: {{ setting('nagad_number') }}

After payment, submit your Transaction ID and Gmail ID for Google Drive access.</div>
      </div>
    </div>

    <div class="card mt">
      <h2>Drive Access Message</h2>
      <div class="copybox">Dear [Student Name],

Your payment has been approved for [Course Name].
Google Drive access has been shared with your Gmail ID.

Please check your Gmail/Google Drive shared section.

Regards,
{{ setting('academy_name') }}</div>
    </div>
    """, setting=setting)
    return render_page("Workflow Guide", body)



@app.route("/backup-database")
@admin_required
def backup_database():
    if not DB_PATH.exists():
        abort(404)
    filename = f"plx_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
    data = DB_PATH.read_bytes()
    return Response(
        data,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route("/security-check")
@admin_required
def security_check():
    checks = [
        ("Debug Mode", "Disabled in production run command"),
        ("CSRF Protection", "Enabled for POST forms"),
        ("Security Headers", "Enabled"),
        ("Rate Limit", f"{MAX_FAILED_LOGINS} failed attempts blocked for {LOGIN_BLOCK_SECONDS//60} minutes"),
        ("Secure Cookie", "Enabled when SESSION_COOKIE_SECURE=true"),
        ("Default Password", "Change immediately after deployment"),
        ("Database Backup", "Available from /backup-database"),
    ]
    body = render_template_string("""
    <div class="card">
      <h2>Security Checklist</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Control</th><th>Status / Instruction</th></tr></thead>
        <tbody>{% for k,v in checks %}<tr><td>{{ k }}</td><td>{{ v }}</td></tr>{% endfor %}</tbody>
      </table></div>
    </div>
    """, checks=checks)
    return render_page("Security Check", body)


@app.route("/audit")
@admin_required
def audit_view():
    rows=q_all("SELECT * FROM audit_trail ORDER BY id DESC LIMIT 1000")
    body=render_template_string("""<div class="table-wrap"><table><thead><tr><th>Time</th><th>User</th><th>Role</th><th>Action</th><th>Details</th></tr></thead><tbody>{% for r in rows %}<tr><td>{{ r.at_time }}</td><td>{{ r.actor_name }}</td><td>{{ r.actor_role }}</td><td>{{ r.action }}</td><td>{{ r.details }}</td></tr>{% endfor %}</tbody></table></div>""", rows=rows)
    return render_page("Audit Trail", body)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
