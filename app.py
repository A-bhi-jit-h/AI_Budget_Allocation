import re, secrets, hashlib, hmac, smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from postgrest.exceptions import APIError

from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client

# ================= CONFIG =================
SMTP_USER = "auth.ai.citizenfeedback@gmail.com"
SMTP_PASS = "wkhx uwrk cukv lhdy"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

SUPABASE_URL = "https://ywhktagmnurhhjpbkayb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3aGt0YWdtbnVyaGhqcGJrYXliIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkwNTIxMTcsImV4cCI6MjA4NDYyODExN30.G7QqdGMFR-zGe8rbRFOXZ2Kzv52TwluOQfhAVIb-S8Y"

OTP_TTL = timedelta(minutes=10)
RESEND_COOLDOWN = 60

# ================= APP =================
app = Flask(__name__)
app.secret_key = "secure-secret"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
PWD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)

# ================= HELPERS =================
def hash_val(v): return hashlib.sha256(v.encode()).hexdigest()
def check_pwd(p): return bool(PWD_RE.match(p))

def send_otp(email, otp):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = email
    msg["Subject"] = "Email OTP Verification"
    msg.set_content(f"Your OTP is {otp}. Valid for 10 minutes.")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

# ================= ROUTES =================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        pwd = hash_val(request.form["password"])
        user = supabase.table("citizens").select("*")\
            .eq("email", email).eq("password_hash", pwd).execute()
        if user.data:
            session["user"] = email
            return redirect("/dashboard")
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form["email"]
        pwd = hash_val(request.form["password"])
        user = supabase.table("citizens").select("*")\
            .eq("email", email).eq("password_hash", pwd).execute()
        if user.data:
            session["user"] = email
            return redirect("/dashboard")
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/start-register")
def start_register():
    return render_template("email_verify.html")

@app.route("/send-otp", methods=["POST"])
def send_otp_route():
    email = request.form["email"]
    if not EMAIL_RE.match(email):
        flash("Invalid email")
        return redirect("/start-register")

    otp = f"{secrets.randbelow(900000) + 100000}"
    now = datetime.utcnow()

    supabase.table("email_otps").insert({
        "email": email,
        "hashed_otp": hash_val(otp),
        "expires_at": (now + OTP_TTL).isoformat(),
        "last_sent_at": now.isoformat()
    }).execute()

    send_otp(email, otp)
    session["reg_email"] = email
    return redirect("/otp")

@app.route("/otp", methods=["GET", "POST"])
def otp():
    if request.method == "POST":
        otp = request.form["otp"]
        email = session.get("reg_email")

        row = supabase.table("email_otps").select("*")\
            .eq("email", email).order("id", desc=True).limit(1).execute()

        if not row.data or not hmac.compare_digest(hash_val(otp), row.data[0]["hashed_otp"]):
            flash("Invalid OTP")
            return redirect("/otp")

        supabase.table("email_otps").delete().eq("id", row.data[0]["id"]).execute()
        return redirect("/register")

    return render_template("otp.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pwd = request.form["password"]
        if not check_pwd(pwd):
            flash("Password must be at least 8 characters with uppercase, lowercase, digit & special character (@$!%*?&)")
            return redirect("/register")

        try:
            supabase.table("citizens").insert({
                "email": session["reg_email"],
                "name": request.form["name"],
                "dob": request.form["dob"],
                "phone": request.form["phone"],
                "password_hash": hash_val(pwd)
            }).execute()

            flash("Profile successfully created!")
            return redirect("/")
        except APIError as e:
            if "duplicate key" in str(e):
                flash("Email already registered. Please login.")
                return redirect("/")
            flash("Profile creation failed. Please try again.")
            return redirect("/register")

    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html", email=session["user"])

@app.route("/complaint")
def complaint():
    if "user" not in session:
        return redirect("/")
    return render_template("complaint.html")

@app.route("/submit-complaint", methods=["POST"])
def submit_complaint():
    if "user" not in session:
        return redirect("/")
    
    try:
        supabase.table("complaints").insert({
            "email": session["user"],
            "title": request.form["complaint_title"],
            "description": request.form["complaint_description"],
            "category": request.form["complaint_category"],
            "location": request.form["complaint_location"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        flash("Complaint submitted successfully!")
        return redirect("/dashboard")
    except APIError as e:
        flash("Failed to submit complaint. Please try again.")
        return redirect("/complaint")

# ================= RUN ==================
if __name__ == "__main__":
    app.run(debug=True)
