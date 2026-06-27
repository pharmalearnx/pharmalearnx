from __future__ import annotations

import csv
import io
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, request, redirect, url_for, session, flash, render_template_string, Response, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "instance" / "plx_enhanced_secure.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_urlsafe(48))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

FAILED_LOGINS = {}
MAX_FAILED_LOGINS = int(os.environ.get("MAX_FAILED_LOGINS", "5"))
LOGIN_BLOCK_SECONDS = int(os.environ.get("LOGIN_BLOCK_SECONDS", "900"))

STYLE = r'''
:root{--primary:#0b63ff;--secondary:#12b8d6;--accent:#ff8a00;--ink:#0f172a;--muted:#64748b;--line:#dbe6f3;--bg:#f4f8ff;--white:#fff;--danger:#b91c1c;--success:#047857;--warning:#a16207;--radius:22px;--shadow:0 18px 50px rgba(15,23,42,.10);--grad:linear-gradient(135deg,#0b63ff,#12b8d6,#ff8a00)}*{box-sizing:border-box}body{margin:0;font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:var(--bg)}a{text-decoration:none;color:inherit}button,input,select,textarea{font:inherit}button{cursor:pointer}.layout{display:grid;grid-template-columns:300px 1fr;min-height:100vh}.sidebar{background:radial-gradient(circle at top right,rgba(18,184,214,.25),transparent 30%),linear-gradient(180deg,#081a35,#102a58);color:#fff;padding:24px;position:sticky;top:0;height:100vh;overflow:auto;display:flex;flex-direction:column;gap:18px}.brand{display:flex;gap:14px;align-items:center;border-bottom:1px solid rgba(255,255,255,.14);padding-bottom:16px}.logo-box{width:74px;height:74px;border-radius:22px;background:#fff;display:grid;place-items:center;overflow:hidden}.logo-box img{width:100%;height:100%;object-fit:contain}.logo-fallback{font-size:30px;font-weight:900;color:#0b63ff}.brand strong{display:block;font-size:26px}.brand small{display:block;color:#dbeafe;font-weight:800}.brand em{display:block;color:rgba(255,255,255,.72);font-style:normal;font-size:11px;margin-top:4px}.side-section{font-size:11px;letter-spacing:1.2px;color:#93c5fd;text-transform:uppercase;margin-top:6px;font-weight:900}nav{display:flex;flex-direction:column;gap:7px}nav a,.userbox button{border:0;border-radius:14px;padding:11px 13px;color:#d7e2f4;background:transparent;font-weight:800;text-align:left}nav a:hover{background:linear-gradient(90deg,rgba(12,77,255,.28),rgba(18,184,214,.18));color:#fff}.userbox{margin-top:auto;border-top:1px solid rgba(255,255,255,.12);padding-top:14px}.userbox button{border:1px solid rgba(255,255,255,.22);width:100%;text-align:center}.topbar{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.90);border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;padding:22px 32px}.topbar p{margin:0;background:var(--grad);-webkit-background-clip:text;color:transparent;font-weight:900;letter-spacing:1px;text-transform:uppercase;font-size:12px}.topbar h1{margin:4px 0 0;font-size:25px}.badge{background:linear-gradient(135deg,rgba(12,77,255,.08),rgba(17,197,190,.10));border:1px solid rgba(12,77,255,.12);border-radius:999px;padding:9px 14px;font-weight:900}.content{padding:32px}.card,.stat,.auth-card,.course-card,.certificate,.table-wrap,.hero,.public-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}.card,.auth-card,.public-card{padding:24px}.auth-card{max-width:620px;margin:30px auto}.hero{padding:38px;background:radial-gradient(circle at top right,rgba(255,138,0,.15),transparent 32%),linear-gradient(135deg,#fff,#edf6ff)}.hero h2{font-size:38px;margin:0 0 12px}.hero p{font-size:17px;color:#475569;line-height:1.6}.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.mt{margin-top:18px}.stat{padding:24px;position:relative;overflow:hidden}.stat:before{content:"";position:absolute;inset:0 0 auto 0;height:5px;background:var(--grad)}.stat span{color:var(--muted);font-weight:800}.stat strong{display:block;font-size:34px;color:var(--primary);margin-top:5px}.page-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:18px}.page-head h2{margin:0;font-size:22px}.course-card{padding:24px;display:flex;flex-direction:column;min-height:300px}.course-card h3{font-size:18px}.tag{display:inline-flex;width:max-content;border-radius:999px;padding:6px 10px;background:linear-gradient(135deg,rgba(12,77,255,.12),rgba(17,197,190,.10));font-weight:900;font-size:12px}.meta{display:flex;gap:8px;flex-wrap:wrap;margin:auto 0 14px}.meta span{background:#f1f5f9;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:800}.primary,.secondary,.danger,.button{border:0;border-radius:999px;min-height:40px;padding:9px 16px;font-weight:900;display:inline-flex;align-items:center;justify-content:center}.primary{background:var(--grad);color:#fff}.secondary{background:#fff;color:var(--primary);border:1px solid var(--line)}.danger{background:#fee2e2;color:var(--danger)}.small{min-height:32px;padding:6px 11px;font-size:13px}label{display:block;font-weight:900;color:#334155;margin:13px 0}input,select,textarea{width:100%;min-height:44px;border:1px solid var(--line);border-radius:13px;padding:10px 12px;margin-top:7px;background:#fff}textarea{resize:vertical}.notice{background:#f8fafc;border:1px solid var(--line);border-radius:15px;padding:13px;line-height:1.6}.notice.warning,.flash.warning{background:#fffbeb;border-color:#fde68a;color:#92400e}.notice.success,.flash.success{background:#ecfdf5;border-color:#99f6e4;color:var(--success)}.flash.danger,.notice.danger{background:#fef2f2;border-color:#fecaca;color:var(--danger)}.flash{padding:13px;margin-bottom:18px;font-weight:800;border-radius:15px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:#fff}th,td{text-align:left;padding:13px;border-bottom:1px solid var(--line);vertical-align:top}th{background:#f1f5f9;color:#475569;text-transform:uppercase;font-size:12px}.inline{display:inline}.chips{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}.chips a,.chip{display:inline-flex;padding:8px 12px;border-radius:999px;background:linear-gradient(135deg,rgba(12,77,255,.08),rgba(17,197,190,.08));border:1px solid rgba(12,77,255,.14);font-weight:800}.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.step{padding:14px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(135deg,rgba(12,77,255,.05),rgba(255,138,0,.05))}.step b{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:var(--grad);color:#fff}.step span{display:block;font-weight:900;margin-top:8px}.step small{color:var(--muted)}.resource-card,.question,.gallery-card,.instructor-card{border:1px solid var(--line);border-radius:18px;padding:16px;margin:14px 0;background:linear-gradient(180deg,#fff,#fbfdff)}.gallery-card img,.instructor-card img{width:100%;height:190px;object-fit:cover;border-radius:16px;background:#eef2ff}.profile-row{display:grid;grid-template-columns:110px 1fr;gap:15px;align-items:start}.profile-row img{width:110px;height:110px;border-radius:18px;object-fit:cover;background:#eef2ff}.option{font-weight:700}.option input{width:auto;min-height:auto}.certificate{text-align:center;border:7px solid #e6eefb;padding:34px;background:radial-gradient(circle at top right,rgba(18,184,214,.13),transparent 34%),linear-gradient(180deg,#fff,#f8fbff);position:relative;overflow:hidden}.certificate:before{content:"";position:absolute;inset:0 0 auto 0;height:8px;background:var(--grad)}.certificate.classic{border-color:#d4af37;background:#fffdf7}.seal{width:76px;height:76px;margin:0 auto 12px;border-radius:50%;display:grid;place-items:center;background:var(--grad);color:#fff;font-weight:900;font-size:22px}.cert-name{font-size:32px;font-weight:900}.cert-course{font-size:20px;font-weight:900;color:var(--primary)}.cert-id{font-weight:900;color:var(--muted)}.copybox{font-family:monospace;white-space:pre-wrap;background:#0f172a;color:#e2e8f0;border-radius:16px;padding:16px;line-height:1.6}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.public-nav{display:flex;gap:10px;flex-wrap:wrap;margin:15px 0}.public-nav a{border:1px solid var(--line);border-radius:999px;padding:9px 13px;font-weight:900;background:#fff}.footer{margin-top:22px;color:#64748b;line-height:1.7}@media print{body *{visibility:hidden}.certificate,.certificate *{visibility:visible}.certificate{position:absolute;left:0;top:0;width:100%;box-shadow:none}.no-print,.sidebar,.topbar{display:none!important}}@media(max-width:1100px){.layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.grid4,.grid3,.grid2,.form-grid{grid-template-columns:1fr}.profile-row{grid-template-columns:1fr}}
'''

BASE = r'''
<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{{ setting('short_name') }} | {{ setting('full_name') }}</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>{{ style }}</style></head><body><div class="layout"><aside class="sidebar"><div class="brand"><div class="logo-box">{% if setting('logo_path') %}<img src="{{ url_for('static', filename=setting('logo_path')) }}" alt="PLX Logo">{% else %}<span class="logo-fallback">{{ setting('short_name') }}</span>{% endif %}</div><div><strong>{{ setting('short_name') }}</strong><small>{{ setting('full_name') }}</small><em>{{ setting('tagline') }}</em></div></div>{% if current_user %}<nav><div class="side-section">Main</div><a href="{{ url_for('dashboard') }}">Dashboard</a><a href="{{ url_for('home') }}">Home Page</a><a href="{{ url_for('courses') }}">Courses</a><a href="{{ url_for('payments') }}">Payments</a><a href="{{ url_for('learning') }}">My Learning</a><a href="{{ url_for('quiz') }}">Quiz</a><a href="{{ url_for('certificates') }}">Certificates</a><a href="{{ url_for('verify') }}">Verify Certificate</a><a href="{{ url_for('change_password') }}">Change Password</a>{% if is_admin %}<div class="side-section">Admin</div><a href="{{ url_for('admin_panel') }}">Admin Panel</a><a href="{{ url_for('drive_access') }}">Drive Access Manager</a><a href="{{ url_for('materials') }}">Course Modules</a><a href="{{ url_for('content_manager') }}">Website Content</a><a href="{{ url_for('categories') }}">Categories</a><a href="{{ url_for('quiz_manager') }}">Quiz Manager</a><a href="{{ url_for('security_check') }}">Security Check</a><a href="{{ url_for('backup_database') }}">Backup Database</a><a href="{{ url_for('student_export') }}">Export Students</a><a href="{{ url_for('audit_view') }}">Audit Trail</a>{% endif %}<a href="{{ url_for('settings') }}">Settings</a></nav><div class="userbox"><p>{{ current_user.name }}<br><small>{{ current_user.email }} • {{ current_user.role }}</small></p><form method="post" action="{{ url_for('logout') }}"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><button>Logout</button></form></div>{% else %}<nav><a href="{{ url_for('home') }}">Home</a><a href="{{ url_for('about') }}">About</a><a href="{{ url_for('courses_public') }}">Courses</a><a href="{{ url_for('instructors') }}">Instructors</a><a href="{{ url_for('gallery') }}">Photo Gallery</a><a href="{{ url_for('contact') }}">Contact</a><a href="{{ url_for('login') }}">Login</a><a href="{{ url_for('register') }}">Student Register</a><a href="{{ url_for('verify') }}">Verify Certificate</a></nav>{% endif %}</aside><main><header class="topbar"><div><p>{{ setting('short_name') }} | {{ setting('academy_name') }}</p><h1>{{ title }}</h1></div><span class="badge">{{ current_user.role|upper if current_user else 'GUEST' }}</span></header><section class="content">{% for category,message in get_flashed_messages(with_categories=true) %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{{ body|safe }}</section></main></div></body></html>
'''


def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def db():
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; con.execute("PRAGMA foreign_keys=ON"); return con
def q_all(sql,args=()):
    with db() as con: return con.execute(sql,args).fetchall()
def q_one(sql,args=()):
    with db() as con: return con.execute(sql,args).fetchone()
def execute(sql,args=()):
    with db() as con:
        cur=con.execute(sql,args); con.commit(); return int(cur.lastrowid or 0)
def setting(key, default=""):
    row=q_one("SELECT value FROM settings WHERE key=?",(key,)); return row["value"] if row else default
def set_setting(key,value): execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value or ""))
def money(value):
    try: return "৳"+f"{float(value):,.0f}"
    except Exception: return "৳0"
def current_user():
    uid=session.get("user_id"); return q_one("SELECT * FROM users WHERE id=? AND active=1",(uid,)) if uid else None
def is_admin():
    u=current_user(); return bool(u and u["role"]=="admin")
def csrf_token():
    token=session.get("_csrf_token")
    if not token: token=secrets.token_urlsafe(32); session["_csrf_token"]=token
    return token
def inject_csrf(body):
    return re.sub(r'(<form\b[^>]*method=["\']post["\'][^>]*>)', r'\1'+f'<input type="hidden" name="_csrf_token" value="{csrf_token()}">', body, flags=re.I)
@app.before_request
def csrf_protect():
    if request.method=="POST":
        form_token=request.form.get("_csrf_token",""); session_token=session.get("_csrf_token","")
        if not form_token or not session_token or not secrets.compare_digest(form_token, session_token): abort(400)
@app.after_request
def add_security_headers(response):
    response.headers["X-Frame-Options"]="DENY"; response.headers["X-Content-Type-Options"]="nosniff"; response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"; response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
    if os.environ.get("ENABLE_HSTS","false").lower()=="true": response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    return response
def render_page(title,body,**ctx): return render_template_string(BASE,title=title,body=inject_csrf(body),style=STYLE,current_user=current_user(),is_admin=is_admin(),setting=setting,money=money,csrf_token=csrf_token,**ctx)
def login_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if not current_user(): flash("Please login first.","warning"); return redirect(url_for("login"))
        return fn(*args,**kwargs)
    return wrapper
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if not is_admin(): flash("Admin access required.","danger"); return redirect(url_for("dashboard"))
        return fn(*args,**kwargs)
    return wrapper
def audit(action,details=""):
    u=current_user(); execute("INSERT INTO audit_trail(at_time,actor_id,actor_name,actor_role,action,details) VALUES(?,?,?,?,?,?)",(now(),u["id"] if u else None,u["name"] if u else "System",u["role"] if u else "system",action,details))
def is_rate_limited(email,ip):
    key=f"{email}|{ip}"; rec=FAILED_LOGINS.get(key)
    if not rec: return False
    count,first=rec
    if time.time()-first>LOGIN_BLOCK_SECONDS: FAILED_LOGINS.pop(key,None); return False
    return count>=MAX_FAILED_LOGINS
def record_failed_login(email,ip):
    key=f"{email}|{ip}"; count,first=FAILED_LOGINS.get(key,(0,time.time())); FAILED_LOGINS[key]=(count+1,first)
def clear_failed_login(email,ip): FAILED_LOGINS.pop(f"{email}|{ip}",None)
def strong_password(password):
    if len(password)<10: return False,"Password must be at least 10 characters."
    if not any(ch.isupper() for ch in password): return False,"Password must include one uppercase letter."
    if not any(ch.islower() for ch in password): return False,"Password must include one lowercase letter."
    if not any(ch.isdigit() for ch in password): return False,"Password must include one number."
    if not any(ch in "!@#$%^&*()-_=+[]{};:,.?/|" for ch in password): return False,"Password must include one special character."
    return True,""
def make_student_password(phone=""):
    digits="".join(ch for ch in (phone or "") if ch.isdigit()); return digits[-6:] if len(digits)>=6 else "Student@123"

def init_db():
    with db() as con:
        con.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,gmail TEXT,phone TEXT,company TEXT,designation TEXT,password_hash TEXT,role TEXT,active INTEGER DEFAULT 1,created_at TEXT);CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE);CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT,title TEXT,category TEXT,other_category TEXT DEFAULT '',duration TEXT,fee REAL,description TEXT,drive_folder_link TEXT,whatsapp_link TEXT DEFAULT '',zoom_link TEXT DEFAULT '',instructor_id INTEGER DEFAULT NULL,active INTEGER DEFAULT 1,created_at TEXT);CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,course_id INTEGER,status TEXT,drive_access_status TEXT DEFAULT 'not_given',access_note TEXT DEFAULT '',score INTEGER,enrolled_at TEXT,completed_at TEXT,UNIQUE(user_id,course_id));CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,enrollment_id INTEGER,user_id INTEGER,course_id INTEGER,method TEXT,amount REAL,wallet_number TEXT,trx_id TEXT,status TEXT DEFAULT 'submitted',submitted_at TEXT,reviewed_at TEXT,note TEXT);CREATE TABLE IF NOT EXISTS resources(id INTEGER PRIMARY KEY AUTOINCREMENT,course_id INTEGER,type TEXT,title TEXT,drive_link TEXT,description TEXT DEFAULT '',active INTEGER DEFAULT 1,created_at TEXT);CREATE TABLE IF NOT EXISTS quizzes(id INTEGER PRIMARY KEY AUTOINCREMENT,course_id INTEGER,question TEXT,option1 TEXT,option2 TEXT,option3 TEXT,option4 TEXT,answer INTEGER);CREATE TABLE IF NOT EXISTS kahoot_links(course_id INTEGER PRIMARY KEY,link TEXT);CREATE TABLE IF NOT EXISTS certificates(id INTEGER PRIMARY KEY AUTOINCREMENT,certificate_code TEXT UNIQUE,user_id INTEGER,course_id INTEGER,score INTEGER,issued_at TEXT);CREATE TABLE IF NOT EXISTS audit_trail(id INTEGER PRIMARY KEY AUTOINCREMENT,at_time TEXT,actor_id INTEGER,actor_name TEXT,actor_role TEXT,action TEXT,details TEXT);CREATE TABLE IF NOT EXISTS instructors(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,title TEXT,profile TEXT,photo_url TEXT,email TEXT,phone TEXT,active INTEGER DEFAULT 1);CREATE TABLE IF NOT EXISTS gallery(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,image_url TEXT,description TEXT,active INTEGER DEFAULT 1,created_at TEXT);''')
        def add_col(table,col,typ):
            try: con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError: pass
        add_col("courses","other_category","TEXT DEFAULT ''"); add_col("courses","whatsapp_link","TEXT DEFAULT ''"); add_col("courses","zoom_link","TEXT DEFAULT ''"); add_col("courses","instructor_id","INTEGER DEFAULT NULL"); add_col("resources","description","TEXT DEFAULT ''"); con.commit()
    defaults={"short_name":"PLX","academy_name":"PharmaLearnX","full_name":"PharmaLearnX Training Platform","tagline":"Pharmaceutical Learning Excellence","email":"Pharmalearnx@gmail.com","phone":"01618881616","contact_address":"Dhaka, Bangladesh","bkash_number":"01618881616","nagad_number":"01618881616","bank_name":"Your Bank Name","bank_account_name":"PharmaLearnX","bank_account_number":"Add account number","card_payment_details":"Card payment details will be provided by admin.","google_drive_email":"Pharmalearnx@gmail.com","facebook_link":"https://www.facebook.com/","youtube_link":"https://www.youtube.com/","whatsapp_link":"https://wa.me/8801618881616","zoom_link":"","home_title":"Professional Pharmaceutical Training Platform","home_subtitle":"Learn GMP, QA, QC, Validation, Audit and Regulatory Affairs through structured professional training.","about_text":"PharmaLearnX provides practical pharmaceutical training focused on GMP, quality systems, regulatory documentation, validation, audit readiness and professional development.","certificate_title":"Certificate of Training Completion","certificate_footer":"Pharmaceutical Learning Excellence","certificate_template":"premium","logo_path":"assets/plx_logo.svg"}
    for k,v in defaults.items(): execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
    admin_email=os.environ.get("ADMIN_EMAIL","admin@pharmalearnx.com"); admin_password=os.environ.get("ADMIN_PASSWORD","ChangeMe@12345!")
    if not q_one("SELECT id FROM users WHERE email=?",(admin_email,)): execute("INSERT INTO users(name,email,gmail,phone,password_hash,role,active,created_at) VALUES(?,?,?,?,?,?,1,?)",(os.environ.get("ADMIN_NAME","PLX Administrator"),admin_email,admin_email,setting("phone"),generate_password_hash(admin_password),"admin",now()))
    if not q_all("SELECT id FROM categories"):
        for c in ["Drug","Drug Substance","Drug Product","GMP","QA","QC","Regulatory Affairs","Validation","Audit","Production","Microbiology","Warehouse","Others"]: execute("INSERT INTO categories(name) VALUES(?)",(c,))
    if not q_all("SELECT id FROM instructors"): execute("INSERT INTO instructors(name,title,profile,photo_url,email,phone,active) VALUES(?,?,?,?,?,?,1)",("Lead Instructor","Pharmaceutical QA & Regulatory Affairs Professional","Experienced trainer in GMP, documentation, validation, audit readiness and regulatory affairs.","",setting("email"),setting("phone")))
    if not q_all("SELECT id FROM courses"):
        instr=q_one("SELECT id FROM instructors ORDER BY id LIMIT 1"); instr_id=instr["id"] if instr else None
        for c in [("GMP-101","Basic GMP for Pharmaceutical Industry","GMP","","2 hours",1000,"GMP principles, documentation and compliance culture."),("GDP-102","Good Documentation Practice & Data Integrity","GMP","","3 hours",1500,"ALCOA+, error correction, audit trail and record review."),("QA-201","Deviation, CAPA & Root Cause Analysis","QA","","4 hours",2000,"Deviation handling, 5-Why, fishbone and CAPA effectiveness."),("RA-401","CTD Module 3 & Dossier Preparation","Regulatory Affairs","","5 hours",3000,"Drug substance/product, specification, validation and stability basics.")]: execute("INSERT INTO courses(code,title,category,other_category,duration,fee,description,drive_folder_link,whatsapp_link,zoom_link,instructor_id,active,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(*c,"","","",instr_id,1,now()))
    if not q_all("SELECT id FROM quizzes"):
        first=q_one("SELECT id FROM courses ORDER BY id LIMIT 1")
        if first:
            for q in [("What does GMP mainly ensure?","Consistent quality standard","Only marketing","Only speed","Only color",1),("Which one is part of ALCOA?","Attributable","Adjustable","Artificial","Avoidable",1),("Main purpose of CAPA is:","Prevent recurrence","Hide deviation","Delete record","Increase batch",1)]: execute("INSERT INTO quizzes(course_id,question,option1,option2,option3,option4,answer) VALUES(?,?,?,?,?,?,?)",(first["id"],*q))

@app.route("/home")
@app.route("/public")
@app.route("/")
def home():
    courses=q_all("SELECT * FROM courses WHERE active=1 ORDER BY id DESC LIMIT 3")
    body=render_template_string('''<div class="hero"><h2>{{ setting('home_title') }}</h2><p>{{ setting('home_subtitle') }}</p><div class="public-nav"><a href="{{ url_for('courses_public') }}">Explore Courses</a><a href="{{ url_for('register') }}">Student Registration</a><a href="{{ url_for('contact') }}">Contact</a></div></div><div class="grid4 mt"><div class="stat"><span>Training Areas</span><strong>10+</strong></div><div class="stat"><span>Certificates</span><strong>Verified</strong></div><div class="stat"><span>Learning Access</span><strong>Drive</strong></div><div class="stat"><span>Support</span><strong>Online</strong></div></div><div class="card mt"><h2>Featured Courses</h2><div class="grid3">{% for c in courses %}<div class="course-card"><span class="tag">{{ c.code }}</span><h3>{{ c.title }}</h3><p>{{ c.description }}</p><div class="meta"><span>{{ c.category if c.category!='Others' else c.other_category or 'Others' }}</span><span>{{ c.duration }}</span><span>{{ money(c.fee) }}</span></div><a class="button primary" href="{{ url_for('register') }}">Enroll Now</a></div>{% endfor %}</div></div>''',courses=courses,setting=setting,money=money)
    return render_page("Home",body)
@app.route("/about")
def about(): return render_page("About",render_template_string('''<div class="card"><h2>About {{ setting('academy_name') }}</h2><p class="notice">{{ setting('about_text') }}</p></div><div class="grid3 mt"><div class="public-card"><h3>Mission</h3><p>To provide practical, job-oriented pharmaceutical training.</p></div><div class="public-card"><h3>Focus</h3><p>GMP, QA, QC, validation, audit, regulatory affairs and documentation.</p></div><div class="public-card"><h3>Learning Model</h3><p>Restricted Google Drive learning access, quiz and certificate verification.</p></div></div>''',setting=setting))
@app.route("/courses-public")
def courses_public(): return render_page("Courses",course_cards(q_all("SELECT * FROM courses WHERE active=1 ORDER BY id DESC"),public=True))
@app.route("/instructors")
def instructors():
    rows=q_all("SELECT * FROM instructors WHERE active=1 ORDER BY id DESC")
    return render_page("Instructor Profile",render_template_string('''<div class="grid2">{% for r in rows %}<div class="instructor-card profile-row">{% if r.photo_url %}<img src="{{ r.photo_url }}" alt="{{ r.name }}">{% else %}<div class="logo-box"><span class="logo-fallback">PLX</span></div>{% endif %}<div><h3>{{ r.name }}</h3><p><strong>{{ r.title }}</strong></p><p>{{ r.profile }}</p><p>{{ r.email }}<br>{{ r.phone }}</p></div></div>{% else %}<p class="notice">No instructor profile added yet.</p>{% endfor %}</div>''',rows=rows))
@app.route("/gallery")
def gallery():
    rows=q_all("SELECT * FROM gallery WHERE active=1 ORDER BY id DESC")
    return render_page("Photo Gallery",render_template_string('''<div class="grid3">{% for r in rows %}<div class="gallery-card">{% if r.image_url %}<img src="{{ r.image_url }}" alt="{{ r.title }}">{% endif %}<h3>{{ r.title }}</h3><p>{{ r.description }}</p></div>{% else %}<p class="notice">No gallery photo added yet.</p>{% endfor %}</div>''',rows=rows))
@app.route("/contact")
def contact():
    return render_page("Contact",render_template_string('''<div class="grid2"><div class="card"><h2>Contact Details</h2><p><strong>Phone:</strong> {{ setting('phone') }}</p><p><strong>Email:</strong> {{ setting('email') }}</p><p><strong>Address:</strong> {{ setting('contact_address') }}</p><p><strong>WhatsApp:</strong> <a target="_blank" href="{{ setting('whatsapp_link') }}">{{ setting('whatsapp_link') }}</a></p><p><strong>Facebook:</strong> <a target="_blank" href="{{ setting('facebook_link') }}">{{ setting('facebook_link') }}</a></p><p><strong>YouTube:</strong> <a target="_blank" href="{{ setting('youtube_link') }}">{{ setting('youtube_link') }}</a></p></div><div class="card"><h2>Payment Details</h2><p><strong>bKash:</strong> {{ setting('bkash_number') }}</p><p><strong>Nagad:</strong> {{ setting('nagad_number') }}</p><p><strong>Bank:</strong> {{ setting('bank_name') }}</p><p><strong>Account Name:</strong> {{ setting('bank_account_name') }}</p><p><strong>Account No:</strong> {{ setting('bank_account_number') }}</p><p><strong>Card:</strong> {{ setting('card_payment_details') }}</p></div></div>''',setting=setting))

def course_cards(courses,public=False,enrollments=None):
    return render_template_string('''<div class="grid3">{% for c in courses %}<div class="course-card"><span class="tag">{{ c.code }}</span><h3>{{ c.title }}</h3><p>{{ c.description }}</p><div class="meta"><span>{{ c.category if c.category!='Others' else c.other_category or 'Others' }}</span><span>{{ c.duration }}</span><span>{{ money(c.fee) }}</span></div>{% if c.whatsapp_link %}<a class="button secondary small" target="_blank" href="{{ c.whatsapp_link }}">WhatsApp Group</a>{% endif %}{% if c.zoom_link %}<a class="button secondary small" target="_blank" href="{{ c.zoom_link }}">Zoom Link</a>{% endif %}{% if public %}<a class="button primary" href="{{ url_for('register') }}">Enroll Now</a>{% elif is_admin %}<a class="button secondary" href="{{ url_for('edit_course', course_id=c.id) }}">Edit Course</a>{% elif enrollments and enrollments.get(c.id) %}<button class="secondary" disabled>{{ enrollments.get(c.id).status.replace('_',' ') }}</button>{% else %}<form method="post" action="{{ url_for('enroll', course_id=c.id) }}"><button class="primary">Enroll & Payment Details</button></form>{% endif %}</div>{% else %}<p class="notice">No course found.</p>{% endfor %}</div>''',courses=courses,public=public,enrollments=enrollments or {},money=money,is_admin=is_admin())

@app.route("/login",methods=["GET","POST"])
def login():
    if current_user(): return redirect(url_for("dashboard"))
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); pw=request.form.get("password",""); ip=request.headers.get("X-Forwarded-For",request.remote_addr or "unknown").split(",")[0].strip()
        if is_rate_limited(email,ip): flash("Too many failed login attempts. Please try again later.","danger"); return redirect(url_for("login"))
        u=q_one("SELECT * FROM users WHERE email=? AND active=1",(email,))
        if u and check_password_hash(u["password_hash"],pw): session.clear(); session["user_id"]=u["id"]; csrf_token(); clear_failed_login(email,ip); audit("USER_LOGIN",email); flash("Login successful.","success"); return redirect(url_for("dashboard"))
        record_failed_login(email,ip); flash("Invalid email or password.","danger")
    return render_page("Login",render_template_string('''<div class="auth-card"><h2>Sign in</h2><p class="notice warning"><strong>Security Note:</strong> Admin password must be managed securely from hosting environment and changed after first login.</p><form method="post"><label>Email <input name="email" type="email" required></label><label>Password <input name="password" type="password" required></label><button class="primary">Login</button><a class="button secondary" href="{{ url_for('register') }}">Student Register</a></form></div>'''))
@app.route("/register",methods=["GET","POST"])
def register():
    if current_user(): return redirect(url_for("dashboard"))
    if request.method=="POST":
        data={k:request.form.get(k,"").strip() for k in ["name","email","gmail","phone","company","designation"]}; pw=request.form.get("password",""); ok,msg=strong_password(pw)
        if not data["name"] or not data["email"] or not ok: flash("Name, email and strong password required. "+msg,"danger"); return redirect(url_for("register"))
        try:
            uid=execute("INSERT INTO users(name,email,gmail,phone,company,designation,password_hash,role,active,created_at) VALUES(?,?,?,?,?,?,?,?,1,?)",(data["name"],data["email"].lower(),data["gmail"],data["phone"],data["company"],data["designation"],generate_password_hash(pw),"student",now())); session["user_id"]=uid; audit("STUDENT_REGISTERED",data["email"]); flash("Registration successful. Please enroll in a course.","success"); return redirect(url_for("courses"))
        except sqlite3.IntegrityError: flash("Email already registered.","danger")
    return render_page("Student Registration",render_template_string('''<div class="auth-card"><h2>Student Registration</h2><form method="post"><label>Full Name <input name="name" required></label><label>Email <input name="email" type="email" required></label><label>Gmail for Google Drive Access <input name="gmail" placeholder="example@gmail.com"></label><label>Phone / WhatsApp <input name="phone"></label><label>Company <input name="company"></label><label>Designation <input name="designation"></label><label>Password <input name="password" type="password" required placeholder="Minimum 10 chars, uppercase, lowercase, number, special"></label><button class="primary">Register</button></form></div>'''))
@app.post("/logout")
def logout(): audit("USER_LOGOUT"); session.clear(); flash("Logged out successfully.","success"); return redirect(url_for("login"))
@app.route("/change-password",methods=["GET","POST"])
@login_required
def change_password():
    u=current_user()
    if request.method=="POST":
        cur=request.form.get("current_password",""); new=request.form.get("new_password",""); conf=request.form.get("confirm_password","")
        if not check_password_hash(u["password_hash"],cur): flash("Current password is incorrect.","danger"); return redirect(url_for("change_password"))
        if new!=conf: flash("New password and confirm password do not match.","danger"); return redirect(url_for("change_password"))
        ok,msg=strong_password(new)
        if not ok: flash(msg,"danger"); return redirect(url_for("change_password"))
        execute("UPDATE users SET password_hash=? WHERE id=?",(generate_password_hash(new),u["id"])); audit("PASSWORD_CHANGED",u["email"]); flash("Password changed successfully.","success"); return redirect(url_for("dashboard"))
    return render_page("Change Password",render_template_string('''<div class="auth-card"><h2>Change Password</h2><form method="post"><label>Current Password <input type="password" name="current_password" required></label><label>New Password <input type="password" name="new_password" required></label><label>Confirm New Password <input type="password" name="confirm_password" required></label><button class="primary">Change Password</button></form></div>'''))

@app.route("/dashboard")
@login_required
def dashboard():
    u=current_user()
    if is_admin():
        stats={"Students":len(q_all("SELECT id FROM users WHERE role='student'")),"Courses":len(q_all("SELECT id FROM courses WHERE active=1")),"Pending Payments":len(q_all("SELECT id FROM payments WHERE status='submitted'")),"Certificates":len(q_all("SELECT id FROM certificates"))}
        recent=q_all("SELECT e.*, u.name user_name, c.title course_title FROM enrollments e JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id ORDER BY e.id DESC LIMIT 8")
        return render_page("Dashboard",render_template_string('''<div class="grid4">{% for k,v in stats.items() %}<div class="stat"><span>{{ k }}</span><strong>{{ v }}</strong></div>{% endfor %}</div><div class="card mt"><h2>Admin Overview</h2><div class="steps"><div class="step"><b>1</b><span>Course Setup</span><small>Add course, modules, Zoom and WhatsApp links.</small></div><div class="step"><b>2</b><span>Enrollment</span><small>Students enroll and submit payment information.</small></div><div class="step"><b>3</b><span>Approval</span><small>Admin approves payment and provides Drive access.</small></div><div class="step"><b>4</b><span>Certificate</span><small>Students complete quiz and receive certificate.</small></div></div></div><div class="card mt"><h2>Recent Enrollments</h2><div class="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Status</th><th>Drive Access</th></tr></thead><tbody>{% for r in recent %}<tr><td>{{ r.user_name }}</td><td>{{ r.course_title }}</td><td>{{ r.status }}</td><td>{{ r.drive_access_status }}</td></tr>{% endfor %}</tbody></table></div></div>''',stats=stats,recent=recent))
    enrolls=q_all("SELECT e.*, c.title course_title, c.code, c.fee FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=? ORDER BY e.id DESC",(u["id"],)); certs=q_all("SELECT id FROM certificates WHERE user_id=?",(u["id"],))
    return render_page("Dashboard",render_template_string('''<div class="grid3"><div class="stat"><span>My Courses</span><strong>{{ enrolls|length }}</strong></div><div class="stat"><span>Certificates</span><strong>{{ certs|length }}</strong></div><div class="stat"><span>Support</span><strong>Active</strong></div></div><div class="card mt"><h2>My Simple Dashboard</h2><p class="notice">Enroll in a course, submit payment details, wait for admin approval, then access course materials from My Learning.</p><div class="chips"><a href="{{ url_for('courses') }}">Enroll Course</a><a href="{{ url_for('payments') }}">Payment</a><a href="{{ url_for('learning') }}">My Learning</a><a href="{{ url_for('certificates') }}">Certificates</a></div></div><div class="card mt"><h2>My Enrollments</h2><div class="table-wrap"><table><thead><tr><th>Course</th><th>Status</th><th>Drive Access</th></tr></thead><tbody>{% for e in enrolls %}<tr><td>{{ e.code }} - {{ e.course_title }}</td><td>{{ e.status.replace('_',' ') }}</td><td>{{ e.drive_access_status.replace('_',' ') }}</td></tr>{% endfor %}</tbody></table></div></div>''',enrolls=enrolls,certs=certs))

@app.route("/courses")
@login_required
def courses():
    selected=request.args.get("category","All"); cats=q_all("SELECT * FROM categories ORDER BY name"); rows=q_all("SELECT * FROM courses WHERE active=1 ORDER BY id DESC") if selected=="All" else q_all("SELECT * FROM courses WHERE active=1 AND category=? ORDER BY id DESC",(selected,)); enrollments={e["course_id"]:e for e in q_all("SELECT * FROM enrollments WHERE user_id=?",(current_user()["id"],))}
    return render_page("Courses",render_template_string('''<div class="page-head"><div><h2>Available Courses</h2><p>Choose a course and continue to payment details.</p></div><form method="get"><label>Category <select name="category"><option value="All">All Categories</option>{% for c in cats %}<option value="{{ c.name }}" {{ 'selected' if selected==c.name else '' }}>{{ c.name }}</option>{% endfor %}</select></label><button class="secondary small">Filter</button></form></div>{{ cards|safe }}''',cats=cats,selected=selected,cards=course_cards(rows,False,enrollments)))
@app.post("/enroll/<int:course_id>")
@login_required
def enroll(course_id):
    if is_admin(): flash("Admin cannot enroll as student.","warning"); return redirect(url_for("courses"))
    course=q_one("SELECT * FROM courses WHERE id=? AND active=1",(course_id,))
    if not course: abort(404)
    try: execute("INSERT INTO enrollments(user_id,course_id,status,enrolled_at) VALUES(?,?,?,?)",(current_user()["id"],course_id,"pending_payment",now()))
    except sqlite3.IntegrityError: pass
    flash("Course enrollment created. Please submit payment details.","success"); return redirect(url_for("payments"))

@app.route("/payments",methods=["GET","POST"])
@login_required
def payments():
    u=current_user()
    if request.method=="POST" and not is_admin():
        eid=int(request.form.get("enrollment_id","0") or 0); method=request.form.get("method",""); wallet=request.form.get("wallet_number","").strip(); trx=request.form.get("trx_id","").strip(); note=request.form.get("note","").strip(); enr=q_one("SELECT * FROM enrollments WHERE id=? AND user_id=?",(eid,u["id"]))
        if not enr: flash("Enrollment not found.","danger"); return redirect(url_for("payments"))
        c=q_one("SELECT * FROM courses WHERE id=?",(enr["course_id"],)); execute("INSERT INTO payments(enrollment_id,user_id,course_id,method,amount,wallet_number,trx_id,status,submitted_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)",(eid,u["id"],enr["course_id"],method,c["fee"],wallet,trx,"submitted",now(),note)); execute("UPDATE enrollments SET status='payment_submitted' WHERE id=?",(eid,)); audit("PAYMENT_SUBMITTED",f"{method} for {c['title']}"); flash("Payment information submitted. Please wait for admin approval.","success"); return redirect(url_for("payments"))
    if is_admin():
        rows=q_all("SELECT p.*, u.name user_name, u.email user_email, u.gmail user_gmail, c.title course_title FROM payments p JOIN users u ON u.id=p.user_id JOIN courses c ON c.id=p.course_id ORDER BY p.id DESC")
        return render_page("Payments",render_template_string('''<div class="card"><h2>Payment Verification</h2><div class="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Method</th><th>Details</th><th>Amount</th><th>Status</th><th>Update</th></tr></thead><tbody>{% for p in rows %}<tr><td>{{ p.user_name }}<br><small>{{ p.user_email }}<br>Gmail: {{ p.user_gmail }}</small></td><td>{{ p.course_title }}</td><td>{{ p.method }}</td><td>Reference: {{ p.wallet_number }}<br>TrxID: {{ p.trx_id }}<br>{{ p.note }}</td><td>{{ money(p.amount) }}</td><td>{{ p.status }}</td><td><form method="post" action="{{ url_for('payment_review', payment_id=p.id) }}"><select name="status"><option>submitted</option><option>approved</option><option>rejected</option></select><button class="primary small">Save</button></form></td></tr>{% endfor %}</tbody></table></div></div>''',rows=rows,money=money))
    payable=q_all("SELECT e.*, c.title course_title, c.fee FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=? AND e.status IN ('pending_payment','payment_rejected')",(u["id"],)); history=q_all("SELECT p.*, c.title course_title FROM payments p JOIN courses c ON c.id=p.course_id WHERE p.user_id=? ORDER BY p.id DESC",(u["id"],))
    return render_page("Payments",render_template_string('''<div class="grid2"><div class="card"><h2>Payment Details</h2><p class="notice success">Submit payment using any approved method, then enter transaction/reference information below.</p><p><strong>bKash:</strong> {{ setting('bkash_number') }}</p><p><strong>Nagad:</strong> {{ setting('nagad_number') }}</p><p><strong>Bank Name:</strong> {{ setting('bank_name') }}</p><p><strong>Account Name:</strong> {{ setting('bank_account_name') }}</p><p><strong>Account Number:</strong> {{ setting('bank_account_number') }}</p><p><strong>Card Details:</strong> {{ setting('card_payment_details') }}</p></div><div class="card"><h2>Submit Payment Information</h2>{% if payable %}<form method="post"><label>Course <select name="enrollment_id">{% for e in payable %}<option value="{{ e.id }}">{{ e.course_title }} - {{ money(e.fee) }}</option>{% endfor %}</select></label><label>Payment Method <select name="method"><option value="bkash">bKash</option><option value="nagad">Nagad</option><option value="card">Card/Bank</option><option value="other">Other</option></select></label><label>Wallet/Card/Bank Reference <input name="wallet_number"></label><label>Transaction ID <input name="trx_id"></label><label>Note <textarea name="note"></textarea></label><button class="primary">Submit Payment</button></form>{% else %}<p class="notice">No pending payment. Please enroll in a course first.</p>{% endif %}</div></div><div class="card mt"><h2>Payment History</h2><div class="table-wrap"><table><thead><tr><th>Course</th><th>Method</th><th>Amount</th><th>Status</th></tr></thead><tbody>{% for p in history %}<tr><td>{{ p.course_title }}</td><td>{{ p.method }}</td><td>{{ money(p.amount) }}</td><td>{{ p.status }}</td></tr>{% endfor %}</tbody></table></div></div>''',payable=payable,history=history,setting=setting,money=money))
@app.post("/payments/<int:payment_id>/review")
@admin_required
def payment_review(payment_id):
    status=request.form.get("status","submitted"); p=q_one("SELECT * FROM payments WHERE id=?",(payment_id,))
    if not p: abort(404)
    execute("UPDATE payments SET status=?, reviewed_at=? WHERE id=?",(status,now(),payment_id)); estatus="paid" if status=="approved" else "payment_rejected" if status=="rejected" else "payment_submitted"; execute("UPDATE enrollments SET status=? WHERE id=?",(estatus,p["enrollment_id"])); audit("PAYMENT_REVIEWED",f"{payment_id}: {status}"); flash("Payment status updated.","success"); return redirect(url_for("payments"))

@app.route("/learning")
@login_required
def learning():
    if is_admin(): rows=q_all("SELECT id course_id, title, drive_folder_link, whatsapp_link, zoom_link, 'given' drive_access_status FROM courses WHERE active=1 ORDER BY id DESC")
    else: rows=q_all("SELECT e.course_id,e.drive_access_status,c.title,c.drive_folder_link,c.whatsapp_link,c.zoom_link FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=? AND e.status IN ('paid','completed')",(current_user()["id"],))
    resource_map={r["course_id"]:q_all("SELECT * FROM resources WHERE course_id=? AND active=1 ORDER BY id DESC",(r["course_id"],)) for r in rows}
    return render_page("My Learning",render_template_string('''<p class="notice success">Course materials are visible only after payment approval. Google Drive access is controlled by admin.</p>{% for row in rows %}<div class="card mt"><h2>{{ row.title }}</h2>{% if row.drive_access_status!='given' %}<p class="notice warning">Payment approved, but Drive access may still be pending.</p>{% endif %}<div class="chips">{% if row.drive_folder_link %}<a target="_blank" href="{{ row.drive_folder_link }}">Course Drive Folder</a>{% endif %}{% if row.whatsapp_link %}<a target="_blank" href="{{ row.whatsapp_link }}">WhatsApp Group</a>{% endif %}{% if row.zoom_link %}<a target="_blank" href="{{ row.zoom_link }}">Zoom Link</a>{% endif %}</div>{% for r in resource_map[row.course_id] %}<div class="resource-card"><span class="tag">{{ r.type }}</span><h3>{{ r.title }}</h3><p>{{ r.description }}</p><a class="button primary" target="_blank" href="{{ r.drive_link }}">Open Module</a></div>{% else %}<p class="notice">No module link added yet.</p>{% endfor %}</div>{% else %}<p class="notice warning">No paid course available. Please enroll and complete payment approval first.</p>{% endfor %}''',rows=rows,resource_map=resource_map))

@app.route("/materials",methods=["GET","POST"])
@admin_required
def materials():
    if request.method=="POST":
        action=request.form.get("action","add")
        if action=="add": execute("INSERT INTO resources(course_id,type,title,drive_link,description,active,created_at) VALUES(?,?,?,?,?,1,?)",(int(request.form.get("course_id")),request.form.get("type"),request.form.get("title","").strip(),request.form.get("drive_link","").strip(),request.form.get("description","").strip(),now())); flash("Course module added.","success")
        elif action=="edit": execute("UPDATE resources SET course_id=?,type=?,title=?,drive_link=?,description=? WHERE id=?",(int(request.form.get("course_id")),request.form.get("type"),request.form.get("title","").strip(),request.form.get("drive_link","").strip(),request.form.get("description","").strip(),int(request.form.get("resource_id")))); flash("Course module updated.","success")
        return redirect(url_for("materials"))
    courses=q_all("SELECT * FROM courses ORDER BY title"); resources=q_all("SELECT r.*, c.title course_title FROM resources r JOIN courses c ON c.id=r.course_id WHERE r.active=1 ORDER BY r.id DESC")
    return render_page("Course Modules",render_template_string('''<div class="grid2"><div class="card"><h2>Add Course Module</h2><form method="post"><input type="hidden" name="action" value="add"><label>Course <select name="course_id">{% for c in courses %}<option value="{{ c.id }}">{{ c.title }}</option>{% endfor %}</select></label><label>Type <select name="type"><option value="pdf">PDF</option><option value="video">Video</option><option value="drive_folder">Drive Folder</option><option value="zoom">Zoom</option><option value="whatsapp">WhatsApp</option><option value="other">Other</option></select></label><label>Title <input name="title" required></label><label>Link <input name="drive_link" required></label><label>Description <textarea name="description"></textarea></label><button class="primary">Add Module</button></form></div><div class="card"><h2>Modules</h2>{% for r in resources %}<div class="resource-card"><h3>{{ r.title }}</h3><p>{{ r.course_title }} • {{ r.type }}</p><p>{{ r.description }}</p><form method="post"><input type="hidden" name="action" value="edit"><input type="hidden" name="resource_id" value="{{ r.id }}"><label>Course <select name="course_id">{% for c in courses %}<option value="{{ c.id }}" {{ 'selected' if c.id==r.course_id else '' }}>{{ c.title }}</option>{% endfor %}</select></label><label>Type <input name="type" value="{{ r.type }}"></label><label>Title <input name="title" value="{{ r.title }}"></label><label>Link <input name="drive_link" value="{{ r.drive_link }}"></label><label>Description <textarea name="description">{{ r.description }}</textarea></label><button class="secondary small">Update</button></form><form method="post" action="{{ url_for('delete_resource', resource_id=r.id) }}"><button class="danger small">Delete</button></form></div>{% else %}<p class="notice">No modules added yet.</p>{% endfor %}</div></div>''',courses=courses,resources=resources))
@app.post("/resources/<int:resource_id>/delete")
@admin_required
def delete_resource(resource_id): execute("UPDATE resources SET active=0 WHERE id=?",(resource_id,)); flash("Course module deleted.","success"); return redirect(url_for("materials"))

# Admin and settings routes continue below

@app.route("/admin", methods=["GET","POST"])
@admin_required
def admin_panel():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "course":
            cat = request.form.get("category","Others")
            other = request.form.get("other_category","").strip()
            if cat == "Others" and other and not q_one("SELECT id FROM categories WHERE name=?", (other,)):
                execute("INSERT INTO categories(name) VALUES(?)", (other,))
            execute("""INSERT INTO courses(code,title,category,other_category,duration,fee,description,drive_folder_link,whatsapp_link,zoom_link,instructor_id,active,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (request.form.get("code","").strip(), request.form.get("title","").strip(), cat, other, request.form.get("duration","").strip(), float(request.form.get("fee") or 0), request.form.get("description","").strip(), request.form.get("drive_folder_link","").strip(), request.form.get("whatsapp_link","").strip(), request.form.get("zoom_link","").strip(), int(request.form.get("instructor_id") or 0) or None, 1, now()))
            flash("Course added.", "success")
        elif action == "student":
            name = request.form.get("student_name","").strip(); email = request.form.get("student_email","").strip().lower(); phone = request.form.get("student_phone","").strip(); password = request.form.get("student_password","").strip() or make_student_password(phone)
            try:
                execute("INSERT INTO users(name,email,gmail,phone,company,designation,password_hash,role,active,created_at) VALUES(?,?,?,?,?,?,?,?,1,?)", (name,email,request.form.get("student_gmail",""),phone,request.form.get("student_company",""),request.form.get("student_designation",""),generate_password_hash(password),"student",now()))
                flash(f"Student added. Temporary password: {password}", "success")
            except sqlite3.IntegrityError:
                flash("Student email already exists.", "danger")
        elif action == "manual_enroll":
            try:
                execute("INSERT INTO enrollments(user_id,course_id,status,enrolled_at) VALUES(?,?,?,?)", (int(request.form.get("manual_user_id")), int(request.form.get("manual_course_id")), request.form.get("manual_status"), now()))
                flash("Enrollment added.", "success")
            except sqlite3.IntegrityError:
                execute("UPDATE enrollments SET status=? WHERE user_id=? AND course_id=?", (request.form.get("manual_status"), int(request.form.get("manual_user_id")), int(request.form.get("manual_course_id"))))
                flash("Enrollment status updated.", "success")
        return redirect(url_for("admin_panel"))
    courses=q_all("SELECT * FROM courses ORDER BY id DESC"); students=q_all("SELECT * FROM users WHERE role='student' ORDER BY id DESC"); users=q_all("SELECT * FROM users ORDER BY id DESC"); cats=q_all("SELECT * FROM categories ORDER BY name"); instructors=q_all("SELECT * FROM instructors WHERE active=1 ORDER BY name")
    return render_page("Admin Panel", render_template_string('''
    <div class="grid2"><div class="card"><h2>Add Course</h2><form method="post"><input type="hidden" name="action" value="course"><div class="form-grid"><label>Course Code <input name="code" required></label><label>Course Title <input name="title" required></label></div><label>Category <select name="category">{% for c in cats %}<option>{{ c.name }}</option>{% endfor %}</select></label><label>If Category is Other, specify here <input name="other_category" placeholder="Specific category name"></label><div class="form-grid"><label>Duration <input name="duration" required></label><label>Fee <input name="fee" type="number" required></label></div><label>Instructor <select name="instructor_id"><option value="">None</option>{% for i in instructors %}<option value="{{ i.id }}">{{ i.name }}</option>{% endfor %}</select></label><label>Google Drive Folder Link <input name="drive_folder_link"></label><label>WhatsApp Link <input name="whatsapp_link" placeholder="https://wa.me/... or group link"></label><label>Zoom Link <input name="zoom_link" placeholder="https://zoom.us/..."></label><label>Description <textarea name="description" required></textarea></label><button class="primary">Add Course</button></form></div><div class="card"><h2>Add Student Manually</h2><form method="post"><input type="hidden" name="action" value="student"><label>Name <input name="student_name" required></label><label>Email <input name="student_email" type="email" required></label><label>Gmail for Drive Access <input name="student_gmail"></label><label>Phone <input name="student_phone"></label><label>Company <input name="student_company"></label><label>Designation <input name="student_designation"></label><label>Temporary Password <input name="student_password" placeholder="Blank = phone last 6 digits"></label><button class="primary">Add Student</button></form></div></div>
    <div class="card mt"><h2>Manual Enrollment</h2><form method="post"><input type="hidden" name="action" value="manual_enroll"><label>Student <select name="manual_user_id">{% for s in students %}<option value="{{ s.id }}">{{ s.name }} - {{ s.email }}</option>{% endfor %}</select></label><label>Course <select name="manual_course_id">{% for c in courses %}<option value="{{ c.id }}">{{ c.title }}</option>{% endfor %}</select></label><label>Status <select name="manual_status"><option value="pending_payment">Pending Payment</option><option value="payment_submitted">Payment Submitted</option><option value="paid">Paid</option><option value="completed">Completed</option></select></label><button class="primary">Save Enrollment</button></form></div>
    <div class="card mt"><h2>Course List</h2><div class="table-wrap"><table><thead><tr><th>Code</th><th>Title</th><th>Category</th><th>Fee</th><th>Status</th><th>Action</th></tr></thead><tbody>{% for c in courses %}<tr><td>{{ c.code }}</td><td>{{ c.title }}</td><td>{{ c.category if c.category!='Others' else c.other_category or 'Others' }}</td><td>{{ money(c.fee) }}</td><td>{{ 'Active' if c.active else 'Inactive' }}</td><td><a class="button secondary small" href="{{ url_for('edit_course', course_id=c.id) }}">Edit</a><form method="post" action="{{ url_for('toggle_course', course_id=c.id) }}" class="inline"><button class="danger small">{{ 'Deactivate' if c.active else 'Activate' }}</button></form></td></tr>{% endfor %}</tbody></table></div></div>
    <div class="card mt"><h2>Users</h2><div class="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Gmail</th><th>Phone</th><th>Role</th><th>Status</th><th>Action</th></tr></thead><tbody>{% for u in users %}<tr><td>{{ u.name }}</td><td>{{ u.email }}</td><td>{{ u.gmail }}</td><td>{{ u.phone }}</td><td>{{ u.role }}</td><td>{{ 'Active' if u.active else 'Inactive' }}</td><td><a class="button secondary small" href="{{ url_for('edit_user', user_id=u.id) }}">Edit</a></td></tr>{% endfor %}</tbody></table></div></div>
    ''', courses=courses, users=users, students=students, cats=cats, instructors=instructors, money=money))

@app.route("/courses/<int:course_id>/edit", methods=["GET","POST"])
@admin_required
def edit_course(course_id):
    c=q_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not c: abort(404)
    cats=q_all("SELECT * FROM categories ORDER BY name"); instructors=q_all("SELECT * FROM instructors WHERE active=1 ORDER BY name")
    if request.method=="POST":
        execute("""UPDATE courses SET code=?,title=?,category=?,other_category=?,duration=?,fee=?,description=?,drive_folder_link=?,whatsapp_link=?,zoom_link=?,instructor_id=? WHERE id=?""", (request.form.get("code"),request.form.get("title"),request.form.get("category"),request.form.get("other_category",""),request.form.get("duration"),float(request.form.get("fee") or 0),request.form.get("description"),request.form.get("drive_folder_link",""),request.form.get("whatsapp_link",""),request.form.get("zoom_link",""),int(request.form.get("instructor_id") or 0) or None,course_id))
        flash("Course updated.", "success"); return redirect(url_for("admin_panel"))
    return render_page("Edit Course", render_template_string('''<div class="card"><h2>Edit Course</h2><form method="post"><label>Code <input name="code" value="{{ c.code }}"></label><label>Title <input name="title" value="{{ c.title }}"></label><label>Category <select name="category">{% for cat in cats %}<option {{ 'selected' if cat.name==c.category else '' }}>{{ cat.name }}</option>{% endfor %}</select></label><label>If Other, specify <input name="other_category" value="{{ c.other_category }}"></label><label>Instructor <select name="instructor_id"><option value="">None</option>{% for i in instructors %}<option value="{{ i.id }}" {{ 'selected' if c.instructor_id==i.id else '' }}>{{ i.name }}</option>{% endfor %}</select></label><label>Duration <input name="duration" value="{{ c.duration }}"></label><label>Fee <input type="number" name="fee" value="{{ c.fee }}"></label><label>Drive Folder Link <input name="drive_folder_link" value="{{ c.drive_folder_link }}"></label><label>WhatsApp Link <input name="whatsapp_link" value="{{ c.whatsapp_link }}"></label><label>Zoom Link <input name="zoom_link" value="{{ c.zoom_link }}"></label><label>Description <textarea name="description">{{ c.description }}</textarea></label><button class="primary">Save Course</button></form></div>''', c=c, cats=cats, instructors=instructors))

@app.post("/courses/<int:course_id>/toggle")
@admin_required
def toggle_course(course_id):
    c=q_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if c: execute("UPDATE courses SET active=? WHERE id=?", (0 if c["active"] else 1, course_id))
    return redirect(url_for("admin_panel"))

@app.route("/users/<int:user_id>/edit", methods=["GET","POST"])
@admin_required
def edit_user(user_id):
    u=q_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not u: abort(404)
    if request.method=="POST":
        execute("UPDATE users SET name=?,email=?,gmail=?,phone=?,company=?,designation=?,role=?,active=? WHERE id=?", (request.form.get("name"),request.form.get("email").lower(),request.form.get("gmail"),request.form.get("phone"),request.form.get("company"),request.form.get("designation"),request.form.get("role"),1 if request.form.get("active")=="1" else 0,user_id))
        flash("User updated.", "success"); return redirect(url_for("admin_panel"))
    return render_page("Edit User", render_template_string('''<div class="card"><h2>Edit User</h2><form method="post"><label>Name <input name="name" value="{{ u.name }}"></label><label>Email <input name="email" value="{{ u.email }}"></label><label>Gmail <input name="gmail" value="{{ u.gmail }}"></label><label>Phone <input name="phone" value="{{ u.phone }}"></label><label>Company <input name="company" value="{{ u.company }}"></label><label>Designation <input name="designation" value="{{ u.designation }}"></label><label>Role <select name="role"><option {{ 'selected' if u.role=='student' else '' }}>student</option><option {{ 'selected' if u.role=='admin' else '' }}>admin</option></select></label><label>Status <select name="active"><option value="1" {{ 'selected' if u.active else '' }}>Active</option><option value="0" {{ 'selected' if not u.active else '' }}>Inactive</option></select></label><button class="primary">Save User</button></form></div>''', u=u))

@app.route("/drive-access", methods=["GET","POST"])
@admin_required
def drive_access():
    if request.method=="POST": execute("UPDATE enrollments SET drive_access_status=?, access_note=? WHERE id=?", (request.form.get("drive_access_status"),request.form.get("access_note",""),int(request.form.get("enrollment_id")))); flash("Drive access status updated.","success"); return redirect(url_for("drive_access"))
    rows=q_all("SELECT e.*, u.name user_name, u.email user_email, u.gmail user_gmail, c.title course_title, c.drive_folder_link FROM enrollments e JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id WHERE e.status IN ('paid','completed') ORDER BY e.id DESC")
    return render_page("Drive Access Manager",render_template_string('''<div class="card"><h2>Google Drive Access Manager</h2><p class="notice">After payment approval, share the Google Drive course folder with the student's Gmail as Viewer and mark access as given.</p><div class="table-wrap"><table><thead><tr><th>Student</th><th>Course</th><th>Gmail</th><th>Folder</th><th>Status</th><th>Update</th></tr></thead><tbody>{% for r in rows %}<tr><td>{{ r.user_name }}<br>{{ r.user_email }}</td><td>{{ r.course_title }}</td><td>{{ r.user_gmail }}</td><td>{% if r.drive_folder_link %}<a target="_blank" href="{{ r.drive_folder_link }}">Open Folder</a>{% endif %}</td><td>{{ r.drive_access_status }}</td><td><form method="post"><input type="hidden" name="enrollment_id" value="{{ r.id }}"><select name="drive_access_status"><option>not_given</option><option>given</option><option>removed</option></select><input name="access_note" value="{{ r.access_note }}"><button class="primary small">Save</button></form></td></tr>{% endfor %}</tbody></table></div></div>''', rows=rows))

@app.route("/content-manager", methods=["GET","POST"])
@admin_required
def content_manager():
    if request.method=="POST":
        action=request.form.get("action")
        if action=="instructor": execute("INSERT INTO instructors(name,title,profile,photo_url,email,phone,active) VALUES(?,?,?,?,?,?,1)",(request.form.get("name"),request.form.get("title"),request.form.get("profile"),request.form.get("photo_url"),request.form.get("email"),request.form.get("phone"))); flash("Instructor profile added.","success")
        elif action=="gallery": execute("INSERT INTO gallery(title,image_url,description,active,created_at) VALUES(?,?,?,1,?)",(request.form.get("title"),request.form.get("image_url"),request.form.get("description"),now())); flash("Gallery photo added.","success")
        return redirect(url_for("content_manager"))
    instructors_rows=q_all("SELECT * FROM instructors WHERE active=1 ORDER BY id DESC"); gallery_rows=q_all("SELECT * FROM gallery WHERE active=1 ORDER BY id DESC")
    return render_page("Website Content",render_template_string('''<div class="grid2"><div class="card"><h2>Add Instructor Profile</h2><form method="post"><input type="hidden" name="action" value="instructor"><label>Name <input name="name" required></label><label>Title <input name="title"></label><label>Photo URL <input name="photo_url"></label><label>Email <input name="email"></label><label>Phone <input name="phone"></label><label>Profile <textarea name="profile"></textarea></label><button class="primary">Add Instructor</button></form></div><div class="card"><h2>Add Gallery Photo</h2><form method="post"><input type="hidden" name="action" value="gallery"><label>Title <input name="title" required></label><label>Image URL <input name="image_url" required></label><label>Description <textarea name="description"></textarea></label><button class="primary">Add Photo</button></form></div></div><div class="grid2 mt"><div class="card"><h2>Instructor List</h2>{% for i in instructors_rows %}<div class="resource-card"><h3>{{ i.name }}</h3><p>{{ i.title }}</p><form method="post" action="{{ url_for('delete_instructor', instructor_id=i.id) }}"><button class="danger small">Delete</button></form></div>{% endfor %}</div><div class="card"><h2>Gallery List</h2>{% for g in gallery_rows %}<div class="resource-card"><h3>{{ g.title }}</h3><p>{{ g.description }}</p><form method="post" action="{{ url_for('delete_gallery', gallery_id=g.id) }}"><button class="danger small">Delete</button></form></div>{% endfor %}</div></div>''', instructors_rows=instructors_rows, gallery_rows=gallery_rows))
@app.post("/instructors/<int:instructor_id>/delete")
@admin_required
def delete_instructor(instructor_id): execute("UPDATE instructors SET active=0 WHERE id=?",(instructor_id,)); return redirect(url_for("content_manager"))
@app.post("/gallery/<int:gallery_id>/delete")
@admin_required
def delete_gallery(gallery_id): execute("UPDATE gallery SET active=0 WHERE id=?",(gallery_id,)); return redirect(url_for("content_manager"))

@app.route("/categories", methods=["GET","POST"])
@admin_required
def categories():
    if request.method=="POST":
        old=request.form.get("old_name","").strip(); name=request.form.get("name","").strip()
        if old: execute("UPDATE categories SET name=? WHERE name=?",(name,old)); execute("UPDATE courses SET category=? WHERE category=?",(name,old))
        elif name:
            try: execute("INSERT INTO categories(name) VALUES(?)",(name,))
            except sqlite3.IntegrityError: pass
        flash("Category saved.","success"); return redirect(url_for("categories"))
    rows=q_all("SELECT * FROM categories ORDER BY name")
    return render_page("Categories",render_template_string('''<div class="grid2"><div class="card"><h2>Add Category</h2><form method="post"><label>Category Name <input name="name" required></label><button class="primary">Save Category</button></form></div><div class="card"><h2>Category List</h2>{% for c in rows %}<div class="resource-card"><form method="post"><input type="hidden" name="old_name" value="{{ c.name }}"><input name="name" value="{{ c.name }}"><button class="secondary small">Edit</button></form>{% if c.name!='Others' %}<form method="post" action="{{ url_for('delete_category', category_id=c.id) }}"><button class="danger small">Delete</button></form>{% endif %}</div>{% endfor %}</div></div>''', rows=rows))
@app.post("/categories/<int:category_id>/delete")
@admin_required
def delete_category(category_id):
    cat=q_one("SELECT * FROM categories WHERE id=?",(category_id,))
    if cat and cat["name"]!="Others": execute("UPDATE courses SET category='Others', other_category=? WHERE category=?",(cat["name"],cat["name"])); execute("DELETE FROM categories WHERE id=?",(category_id,))
    return redirect(url_for("categories"))

@app.route("/quiz", methods=["GET","POST"])
@login_required
def quiz():
    if is_admin(): return redirect(url_for("quiz_manager"))
    eligible=q_all("SELECT e.*,c.title course_title FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=? AND e.status='paid'",(current_user()["id"],))
    cid=int(request.values.get("course_id") or (eligible[0]["course_id"] if eligible else 0)); questions=q_all("SELECT * FROM quizzes WHERE course_id=?",(cid,)) if cid else []; kahoot=q_one("SELECT * FROM kahoot_links WHERE course_id=?",(cid,)) if cid else None
    if request.method=="POST" and request.form.get("submit_quiz"):
        score=sum(1 for q in questions if request.form.get(f"q_{q['id']}") and int(request.form.get(f"q_{q['id']}")==str(q["answer"])))
        # fix scoring reliably
        score=sum(1 for q in questions if request.form.get(f"q_{q['id']}") and int(request.form.get(f"q_{q['id']}"))==q["answer"])
        pct=round(score/len(questions)*100) if questions else 0
        if pct<70: flash(f"Not passed. Score: {pct}%.","danger"); return redirect(url_for("quiz",course_id=cid))
        execute("UPDATE enrollments SET status='completed', score=?, completed_at=? WHERE user_id=? AND course_id=?",(pct,now(),current_user()["id"],cid))
        if not q_one("SELECT id FROM certificates WHERE user_id=? AND course_id=?",(current_user()["id"],cid)):
            code=f"PLX-{datetime.now().year}-{len(q_all('SELECT id FROM certificates'))+1:04d}"; execute("INSERT INTO certificates(certificate_code,user_id,course_id,score,issued_at) VALUES(?,?,?,?,?)",(code,current_user()["id"],cid,pct,now()))
        flash("Quiz passed. Certificate generated.","success"); return redirect(url_for("certificates"))
    return render_page("Quiz",render_template_string('''<div class="card">{% if eligible %}<form method="get"><label>Select Course <select name="course_id">{% for e in eligible %}<option value="{{ e.course_id }}" {{ 'selected' if cid==e.course_id else '' }}>{{ e.course_title }}</option>{% endfor %}</select></label><button class="secondary small">Load Quiz</button></form>{% if kahoot and kahoot.link %}<p class="notice success">Kahoot: <a target="_blank" href="{{ kahoot.link }}">Open Kahoot Quiz</a></p>{% endif %}{% if questions %}<form method="post"><input type="hidden" name="course_id" value="{{ cid }}">{% for q in questions %}<div class="question"><h3>{{ loop.index }}. {{ q.question }}</h3>{% for n,opt in [(1,q.option1),(2,q.option2),(3,q.option3),(4,q.option4)] %}<label class="option"><input type="radio" name="q_{{ q.id }}" value="{{ n }}" required> {{ opt }}</label>{% endfor %}</div>{% endfor %}<button class="primary" name="submit_quiz" value="1">Submit Quiz</button></form>{% else %}<p class="notice">No quiz added for this course.</p>{% endif %}{% else %}<p class="notice warning">No paid course available for quiz.</p>{% endif %}</div>''',eligible=eligible,cid=cid,questions=questions,kahoot=kahoot))

@app.route("/quiz-manager", methods=["GET","POST"])
@admin_required
def quiz_manager():
    courses=q_all("SELECT * FROM courses ORDER BY title"); cid=int(request.values.get("course_id") or (courses[0]["id"] if courses else 0))
    if request.method=="POST":
        action=request.form.get("action")
        if action=="kahoot": execute("INSERT INTO kahoot_links(course_id,link) VALUES(?,?) ON CONFLICT(course_id) DO UPDATE SET link=excluded.link",(cid,request.form.get("kahoot_link","")))
        elif action=="quiz":
            qid=request.form.get("quiz_id"); vals=(cid,request.form.get("question",""),request.form.get("option1",""),request.form.get("option2",""),request.form.get("option3",""),request.form.get("option4",""),int(request.form.get("answer","1")))
            if qid: execute("UPDATE quizzes SET course_id=?,question=?,option1=?,option2=?,option3=?,option4=?,answer=? WHERE id=?",(*vals,int(qid)))
            else: execute("INSERT INTO quizzes(course_id,question,option1,option2,option3,option4,answer) VALUES(?,?,?,?,?,?,?)",vals)
        flash("Quiz information saved.","success"); return redirect(url_for("quiz_manager",course_id=cid))
    qs=q_all("SELECT * FROM quizzes WHERE course_id=? ORDER BY id DESC",(cid,)); kahoot=q_one("SELECT * FROM kahoot_links WHERE course_id=?",(cid,))
    return render_page("Quiz Manager",render_template_string('''<div class="grid2"><div class="card"><h2>Quiz Setup</h2><form method="get"><label>Course <select name="course_id">{% for c in courses %}<option value="{{ c.id }}" {{ 'selected' if cid==c.id else '' }}>{{ c.title }}</option>{% endfor %}</select></label><button class="secondary small">Load</button></form><form method="post" class="resource-card"><input type="hidden" name="action" value="kahoot"><input type="hidden" name="course_id" value="{{ cid }}"><label>Kahoot Link <input name="kahoot_link" value="{{ kahoot.link if kahoot else '' }}"></label><button class="primary">Save Kahoot Link</button></form><form method="post" class="resource-card"><input type="hidden" name="action" value="quiz"><label>Question <input name="question" required></label><label>Option 1 <input name="option1" required></label><label>Option 2 <input name="option2" required></label><label>Option 3 <input name="option3" required></label><label>Option 4 <input name="option4" required></label><label>Correct Answer <select name="answer"><option value="1">Option 1</option><option value="2">Option 2</option><option value="3">Option 3</option><option value="4">Option 4</option></select></label><button class="primary">Add Question</button></form></div><div class="card"><h2>Questions</h2>{% for q in qs %}<div class="resource-card"><h3>{{ q.question }}</h3><p>Correct: Option {{ q.answer }}</p><form method="post"><input type="hidden" name="action" value="quiz"><input type="hidden" name="quiz_id" value="{{ q.id }}"><input name="question" value="{{ q.question }}"><input name="option1" value="{{ q.option1 }}"><input name="option2" value="{{ q.option2 }}"><input name="option3" value="{{ q.option3 }}"><input name="option4" value="{{ q.option4 }}"><select name="answer">{% for n in [1,2,3,4] %}<option value="{{ n }}" {{ 'selected' if q.answer==n else '' }}>Option {{ n }}</option>{% endfor %}</select><button class="secondary small">Update</button></form><form method="post" action="{{ url_for('delete_quiz', quiz_id=q.id) }}"><button class="danger small">Delete</button></form></div>{% endfor %}</div></div>''',courses=courses,cid=cid,qs=qs,kahoot=kahoot))
@app.post("/quiz-manager/<int:quiz_id>/delete")
@admin_required
def delete_quiz(quiz_id):
    row=q_one("SELECT course_id FROM quizzes WHERE id=?",(quiz_id,)); cid=row["course_id"] if row else 0; execute("DELETE FROM quizzes WHERE id=?",(quiz_id,)); return redirect(url_for("quiz_manager",course_id=cid))

def cert_html(cert):
    return render_template_string('''<div class="certificate {{ setting('certificate_template') }}"><div class="seal">{{ setting('short_name') }}</div><h2>{{ setting('certificate_title') }}</h2><p>This is to certify that</p><div class="cert-name">{{ cert.user_name }}</div><p>has successfully completed the training course</p><div class="cert-course">{{ cert.course_title }}</div><p>Score: {{ cert.score }}% • Issued: {{ cert.issued_at }}</p><p class="cert-id">Certificate ID: {{ cert.certificate_code }}</p><p>{{ setting('certificate_footer') }}</p><a class="button secondary no-print" href="{{ url_for('verify', certificate_code=cert.certificate_code) }}">Verify Online</a></div>''',cert=cert,setting=setting)
@app.route("/certificates")
@login_required
def certificates():
    rows=q_all("SELECT cert.*,u.name user_name,c.title course_title FROM certificates cert JOIN users u ON u.id=cert.user_id JOIN courses c ON c.id=cert.course_id "+("" if is_admin() else "WHERE cert.user_id=? ")+"ORDER BY cert.id DESC",() if is_admin() else (current_user()["id"],))
    return render_page("Certificates",render_template_string("<div class='grid2'>{% for cert in rows %}{{ cert_html(cert)|safe }}{% else %}<p class='notice'>No certificate found.</p>{% endfor %}</div>",rows=rows,cert_html=cert_html))
@app.route("/verify")
def verify():
    code=request.args.get("certificate_code","").strip(); cert=q_one("SELECT cert.*,u.name user_name,c.title course_title FROM certificates cert JOIN users u ON u.id=cert.user_id JOIN courses c ON c.id=cert.course_id WHERE cert.certificate_code=?",(code,)) if code else None
    return render_page("Verify Certificate",render_template_string('''<div class="card"><h2>Certificate Verification</h2><form method="get"><label>Certificate ID <input name="certificate_code" value="{{ code }}" placeholder="PLX-2026-0001"></label><button class="primary">Verify</button></form></div>{% if code %}{% if cert %}<div class="flash success mt">Certificate verified successfully.</div>{{ cert_html(cert)|safe }}{% else %}<div class="flash danger mt">Certificate not found.</div>{% endif %}{% endif %}''',code=code,cert=cert,cert_html=cert_html))

@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    if not is_admin():
        u=current_user()
        if request.method=="POST": execute("UPDATE users SET name=?,gmail=?,phone=?,company=?,designation=? WHERE id=?",(request.form.get("name"),request.form.get("gmail"),request.form.get("phone"),request.form.get("company"),request.form.get("designation"),u["id"])); flash("Profile updated.","success"); return redirect(url_for("settings"))
        return render_page("Profile",render_template_string("<div class='card'><h2>My Profile</h2><form method='post'><label>Name <input name='name' value='{{ u.name }}'></label><label>Email <input value='{{ u.email }}' disabled></label><label>Gmail <input name='gmail' value='{{ u.gmail }}'></label><label>Phone <input name='phone' value='{{ u.phone }}'></label><label>Company <input name='company' value='{{ u.company }}'></label><label>Designation <input name='designation' value='{{ u.designation }}'></label><button class='primary'>Save Profile</button></form></div>",u=u))
    keys=["short_name","academy_name","full_name","tagline","email","phone","contact_address","bkash_number","nagad_number","bank_name","bank_account_name","bank_account_number","card_payment_details","google_drive_email","facebook_link","youtube_link","whatsapp_link","zoom_link","home_title","home_subtitle","about_text","certificate_title","certificate_footer","certificate_template","logo_path"]
    if request.method=="POST":
        for k in keys: set_setting(k,request.form.get(k,""))
        flash("Settings updated.","success"); return redirect(url_for("settings"))
    return render_page("Settings",render_template_string('''<div class="card"><h2>Editable Settings</h2><p class="notice">Update logo path, contact details, social links, payment numbers, bank/card details, homepage text and certificate text.</p><form method="post">{% for k in keys %}<label>{{ k.replace('_',' ').title() }}{% if k in ['about_text','home_subtitle','card_payment_details'] %}<textarea name="{{ k }}">{{ setting(k) }}</textarea>{% elif k=='certificate_template' %}<select name="{{ k }}"><option value="premium" {{ 'selected' if setting(k)=='premium' else '' }}>premium</option><option value="classic" {{ 'selected' if setting(k)=='classic' else '' }}>classic</option></select>{% else %}<input name="{{ k }}" value="{{ setting(k) }}">{% endif %}</label>{% endfor %}<button class="primary">Save Settings</button></form></div>''',keys=keys,setting=setting))

@app.route("/security-check")
@admin_required
def security_check():
    checks=[("CSRF Protection","Enabled"),("Debug Mode","Off in run.py/gunicorn"),("Password Change","Available for admin and student"),("Failed Login Limit",f"{MAX_FAILED_LOGINS} attempts"),("Course Materials","Only paid/completed students can view"),("Database Backup","Available for admin")]
    return render_page("Security Check",render_template_string("<div class='card'><h2>Security Checklist</h2><div class='table-wrap'><table><thead><tr><th>Control</th><th>Status</th></tr></thead><tbody>{% for c,s in checks %}<tr><td>{{ c }}</td><td>{{ s }}</td></tr>{% endfor %}</tbody></table></div></div>",checks=checks))
@app.route("/backup-database")
@admin_required
def backup_database():
    if not DB_PATH.exists(): abort(404)
    return Response(DB_PATH.read_bytes(),mimetype="application/octet-stream",headers={"Content-Disposition":f"attachment; filename=plx_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"})
@app.route("/student-export")
@admin_required
def student_export():
    rows=q_all("SELECT u.name,u.email,u.gmail,u.phone,u.company,u.designation,c.title course_title,e.status,e.drive_access_status FROM enrollments e JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id ORDER BY e.id DESC")
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Name","Email","Gmail","Phone","Company","Designation","Course","Status","Drive Access"])
    for r in rows: w.writerow([r["name"],r["email"],r["gmail"],r["phone"],r["company"],r["designation"],r["course_title"],r["status"],r["drive_access_status"]])
    return Response(out.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=plx_students.csv"})
@app.route("/audit")
@admin_required
def audit_view():
    rows=q_all("SELECT * FROM audit_trail ORDER BY id DESC LIMIT 1000")
    return render_page("Audit Trail",render_template_string("<div class='table-wrap'><table><thead><tr><th>Time</th><th>User</th><th>Role</th><th>Action</th><th>Details</th></tr></thead><tbody>{% for r in rows %}<tr><td>{{ r.at_time }}</td><td>{{ r.actor_name }}</td><td>{{ r.actor_role }}</td><td>{{ r.action }}</td><td>{{ r.details }}</td></tr>{% endfor %}</tbody></table></div>",rows=rows))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
