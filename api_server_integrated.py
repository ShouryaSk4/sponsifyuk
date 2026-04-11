"""
SponsifyUK – API Server
=======================
Flask backend that serves the SponsifyUK job-search frontend.

Frontend pages and what they need
-----------------------------------
login.html        POST /api/users/login        { username, password }
register.html     POST /api/users/register     { email, password, confirm_password }
contact-us.html   POST /api/contact            { name, email, msg_subject, phone_number, message }
job-listing.html  GET  /api/jobs/search        ?q=&location=&category=&page=&limit=
                  GET  /api/filters            (populate sidebar dropdowns)
job-details.html  GET  /api/jobs/<id>
index.html        GET  /api/jobs/featured      (homepage job cards)
dashboard.html    GET  /api/users/me           (name, stats, saved jobs, invoices)
pricing.htm       POST /api/users/<id>/upgrade
Any page          POST /api/users/logout
                  GET  /api/health
"""

from flask import Flask, request, jsonify, g, session
from flask_cors import CORS
from job_search_engine import JobSearchEngine
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
import stripe
import os
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("SECRET_KEY")

# ── App Setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True,
     origins=[
         "https://api.aztechinfoway.com",
         "https://sponsifyuk.aztechinfoway.com",
         "http://localhost", "http://127.0.0.1",
         "http://localhost:5500", "http://localhost:8080", "http://localhost:5173", "null"
     ])

# ── DB Setup (FIXED ABSOLUTE PATH) ───────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "jobs.db")


def get_db():
    if "db" not in g:
        print("USING DB:", DB_PATH)  # keep for debugging (remove later)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()
      
search_engine = JobSearchEngine(db_path=DB_PATH)

# ── Job Category Mapping ──────────────────────────────────────────────────────
JOB_CATEGORIES_MAP = {
    1:  {"name": "Technology & IT",       "icon": "fas fa-laptop-code"},
    2:  {"name": "Finance & Accounting",  "icon": "fas fa-chart-line"},
    3:  {"name": "Healthcare & Medical",  "icon": "fas fa-heartbeat"},
    4:  {"name": "Sales & Marketing",     "icon": "fas fa-bullhorn"},
    5:  {"name": "Engineering",           "icon": "fas fa-cogs"},
    6:  {"name": "Education & Training",  "icon": "fas fa-graduation-cap"},
    7:  {"name": "Legal & Compliance",    "icon": "fas fa-gavel"},
    8:  {"name": "HR & Recruitment",      "icon": "fas fa-users"},
    9:  {"name": "Creative & Design",     "icon": "fas fa-paint-brush"},
    10: {"name": "Operations & Logistics","icon": "fas fa-truck"},
    11: {"name": "Other",                 "icon": "fas fa-briefcase"},
}


# ── DB Helpers ────────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=20.0)
        g.db.execute("PRAGMA journal_mode=WAL;")
        g.db.execute("PRAGMA busy_timeout=20000;")
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def hash_pw(password: str) -> str:
    """SHA-256 password hash. Swap for bcrypt in production."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ── Auth: Register ────────────────────────────────────────────────────────────

@app.route("/api/users/register", methods=["POST"])
def register_user():
    """
    Called by the Register button on register.html.

    Frontend field IDs  →  JSON keys we accept
    ─────────────────────────────────────────────
    #email2             →  email  (used as username)
    #password2          →  password
    #password3          →  confirm_password
    """
    data = request.get_json(silent=True) or {}

    # Accept both raw field names and the HTML id names
    username = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or data.get("password2") or ""
    confirm  = data.get("confirm_password") or data.get("password3") or ""

    # ── Validation ──
    if not username or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400
    if confirm and password != confirm:
        return jsonify({"success": False, "error": "Passwords do not match."}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400

    # Derive display name from email prefix if not supplied
    first_name = (data.get("first_name") or username.split("@")[0]).strip()
    last_name  = (data.get("last_name") or "").strip()

    db     = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        return jsonify({"success": False, "error": "An account with this email already exists."}), 409

    email = (data.get("email") or username).strip()

    cursor.execute(
        """
        INSERT INTO users
            (username, password, first_name, last_name,
             job_role_profession, phone_number, membership_status, email)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            username,
            hash_pw(password),
            first_name,
            last_name,
            data.get("job_role_profession", ""),
            data.get("phone_number", ""),
            email,
        ),
    )
    user_id = cursor.lastrowid
    db.commit()

    # Auto-login
    session["user_id"]    = user_id
    session["username"]   = username
    session["is_premium"] = False

    return jsonify({
        "success":  True,
        "user_id":  user_id,
        "message":  "Account created successfully.",
        "redirect": "dashboard.html",
        "user": {
            "user_id":             user_id,
            "username":            username,
            "first_name":          first_name,
            "last_name":           last_name,
            "full_name":           f"{first_name} {last_name}".strip(),
            "job_role_profession": data.get("job_role_profession", ""),
            "phone_number":        data.get("phone_number", ""),
            "membership_status":   0,
            "is_premium":          False,
            "saved_jobs":          [],
        },
    }), 201


# ── Auth: Login ───────────────────────────────────────────────────────────────

@app.route("/api/users/login", methods=["POST"])
def login_user():
    """
    Called by the Login button on login.html.

    Frontend field IDs  →  JSON keys we accept
    ─────────────────────────────────────────────
    #email              →  username  (or email)
    #password           →  password
    """
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    db     = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT user_id, username, first_name, last_name,
               job_role_profession, phone_number, membership_status, saved_jobs
        FROM   users
        WHERE  (username = ? OR email = ?) AND password = ?
        """,
        (username, username, hash_pw(password)),
    )
    user = cursor.fetchone()

    if not user:
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

    cursor.execute(
        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
        (user["user_id"],),
    )
    db.commit()

    session["user_id"]    = user["user_id"]
    session["username"]   = user["username"]
    session["is_premium"] = user["membership_status"] == 1

    return jsonify({
        "success":  True,
        "redirect": "dashboard.html",
        "user": {
            "user_id":             user["user_id"],
            "username":            user["username"],
            "first_name":          user["first_name"],
            "last_name":           user["last_name"],
            "full_name":           f"{user['first_name']} {user['last_name']}".strip(),
            "job_role_profession": user["job_role_profession"],
            "phone_number":        user["phone_number"],
            "membership_status":   user["membership_status"],
            "is_premium":          user["membership_status"] == 1,
            "saved_jobs":          json.loads(user["saved_jobs"]) if user["saved_jobs"] else [],
        },
    })


# ── Auth: Logout ──────────────────────────────────────────────────────────────

@app.route("/api/users/logout", methods=["POST"])
def logout_user():
    session.clear()
    return jsonify({"success": True, "redirect": "index.html"})


# ── Track Job Application Click ───────────────────────────────────────────────

@app.route("/api/users/<int:user_id>/apply", methods=["POST"])
def track_user_application(user_id):
    """
    Called by app.js when a user clicks "Apply Now" on job-details.html.
    Records the click in the user_usage table for analytics.
    """
    data = request.get_json(silent=True) or {}
    company_name    = data.get("company_name", "")
    search_keywords = data.get("search_keywords", "")

    db     = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO user_usage (user_id, search_keywords, companies_applied)
        VALUES (?, ?, ?)
        """,
        (user_id, search_keywords, company_name),
    )
    db.commit()

    return jsonify({"success": True, "message": "Application tracked."})


# ── Current User (session-based) ──────────────────────────────────────────────

@app.route("/api/users/me", methods=["GET"])
def get_current_user():
    """
    Called on every page load by app.js to check whether the user is
    logged in and to populate the nav / dashboard with their name.
    Returns 401 (unauthenticated) if no session exists — not an error,
    just means the user is a guest.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "authenticated": False}), 401

    db     = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT user_id, username, first_name, last_name, job_role_profession,
               phone_number, membership_status, saved_jobs,
               resume_storage_link, ai_improved_resume, created_at, last_login
        FROM   users
        WHERE  user_id = ?
        """,
        (user_id,),
    )
    user = cursor.fetchone()

    if not user:
        session.clear()
        return jsonify({"success": False, "authenticated": False}), 401

    # Aggregate dashboard stats in one extra query
    cursor.execute(
        """
        SELECT COUNT(*) AS total_searches,
               SUM(CASE WHEN companies_applied IS NOT NULL THEN 1 ELSE 0 END) AS total_applications
        FROM   user_usage
        WHERE  user_id = ?
        """,
        (user_id,),
    )
    stats    = cursor.fetchone()
    saved_ids = json.loads(user["saved_jobs"]) if user["saved_jobs"] else []

    return jsonify({
        "success":       True,
        "authenticated": True,
        "user": {
            "user_id":             user["user_id"],
            "username":            user["username"],
            "first_name":          user["first_name"],
            "last_name":           user["last_name"],
            "full_name":           f"{user['first_name']} {user['last_name']}".strip(),
            "job_role_profession": user["job_role_profession"],
            "phone_number":        user["phone_number"],
            "membership_status":   user["membership_status"],
            "is_premium":          user["membership_status"] == 1,
            "saved_jobs":          saved_ids,
            "resume_storage_link": user["resume_storage_link"],
            "ai_improved_resume":  user["ai_improved_resume"],
            "created_at":          user["created_at"],
            "last_login":          user["last_login"],
        },
        "stats": {
            "saved_jobs":         len(saved_ids),
            "total_searches":     stats["total_searches"]     or 0,
            "total_applications": stats["total_applications"] or 0,
        },
    })


# ── User Profile (by ID) ──────────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user_profile(user_id):
    db     = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT user_id, username, first_name, last_name, job_role_profession,
               phone_number, membership_status, saved_jobs,
               resume_storage_link, ai_improved_resume, created_at, last_login
        FROM   users WHERE user_id = ?
        """,
        (user_id,),
    )
    user = cursor.fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    return jsonify({
        "success": True,
        "user": {
            "user_id":             user["user_id"],
            "username":            user["username"],
            "first_name":          user["first_name"],
            "last_name":           user["last_name"],
            "full_name":           f"{user['first_name']} {user['last_name']}".strip(),
            "job_role_profession": user["job_role_profession"],
            "phone_number":        user["phone_number"],
            "membership_status":   user["membership_status"],
            "is_premium":          user["membership_status"] == 1,
            "saved_jobs":          json.loads(user["saved_jobs"]) if user["saved_jobs"] else [],
            "resume_storage_link": user["resume_storage_link"],
            "ai_improved_resume":  user["ai_improved_resume"],
            "created_at":          user["created_at"],
            "last_login":          user["last_login"],
        },
    })


@app.route("/api/users/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    data   = request.get_json(silent=True) or {}
    db     = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        return jsonify({"success": False, "error": "User not found."}), 404

    allowed = [
        "first_name", "last_name", "job_role_profession",
        "phone_number", "membership_status",
        "resume_storage_link", "ai_improved_resume",
    ]
    fields, values = [], []
    for f in allowed:
        if f in data:
            fields.append(f"{f} = ?")
            values.append(data[f])

    if "new_password" in data:
        fields.append("password = ?")
        values.append(hash_pw(data["new_password"]))

    if not fields:
        return jsonify({"success": False, "error": "No valid fields to update."}), 400

    values.append(user_id)
    cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?", values)
    db.commit()

    return jsonify({"success": True, "message": "Profile updated."})


# ── Upgrade to Premium ────────────────────────────────────────────────────────

@app.route("/api/create-checkout-session", methods=["POST"])
def create_checkout_session():
    """
    Called when the user clicks a plan button on Pricing.jsx.
    Accepts { user_id, tier } in the body.
    Tier is 1 (£10), 2 (£20), or 3 (£30).
    """
    data    = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    tier    = int(data.get("tier", 1))

    if not user_id:
        return jsonify({"success": False, "error": "user_id is required."}), 400

    db     = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT user_id, membership_status, email FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    if user["membership_status"] == tier and tier != 0:
        return jsonify({
            "success":         True,
            "already_premium": True,
            "message":         "You already have this Premium tier.",
        })
        
    # Map tier to amount and plan name
    if tier == 1:
        amount = 10
        plan_name = "Plan 1 (Top 1000 Jobs)"
    elif tier == 2:
        amount = 20
        plan_name = "Plan 2 (Top 3000 Jobs)"
    elif tier == 3:
        amount = 30
        plan_name = "Plan 3 (Unlimited Access)"
    else:
        return jsonify({"success": False, "error": "Invalid tier limit."}), 400

    try:
        # Create pending payment record
        cursor.execute(
            "INSERT INTO payments (user_id, amount, status) VALUES (?, ?, 'pending')",
            (user_id, amount),
        )
        db.commit()

        # Create Stripe Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=user["email"], # useful if they added an email
            client_reference_id=str(user_id), # We use this to identify them in the webhook
            metadata={'tier': str(tier)},
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': plan_name,
                        'description': f'SponsifyUK {plan_name} Subscription',
                    },
                    'unit_amount': int(amount * 100), # Stripe expects pennies/cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://localhost:5173/job-listing?payment=success',
            cancel_url='http://localhost:5173/pricing?payment=cancelled',
        )

        return jsonify({
            "success":      True,
            "checkout_url": session.url
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        # For testing without endpoint secret verification:
        event = json.loads(payload)
    except Exception as e:
        return jsonify(success=False), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Fulfill the purchase based on client_reference_id
        user_id = session.get('client_reference_id')
        transaction_id = session.get('payment_intent') or session.get('id')
        
        if user_id:
            db = get_db()
            cursor = db.cursor()
            
            # Extract tier from metadata, default to 1 for backwards compatibility
            tier = int(session.get('metadata', {}).get('tier', 1))
            
            # Upgrade user
            cursor.execute("UPDATE users SET membership_status = ? WHERE user_id = ?", (tier, user_id))
            
            # Update pending payment or insert if missing
            cursor.execute("UPDATE payments SET status = 'success', transaction_id = ? WHERE user_id = ? AND status = 'pending'", (transaction_id, user_id))
            if cursor.rowcount == 0:
                 amount_total = session.get('amount_total', 0) / 100.0
                 cursor.execute(
                    "INSERT INTO payments (user_id, amount, transaction_id, status) VALUES (?, ?, ?, 'success')",
                    (user_id, amount_total, transaction_id)
                 )
            db.commit()

    return jsonify(success=True), 200



# ── Saved Jobs ────────────────────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>/saved-jobs", methods=["GET", "POST", "DELETE"])
def manage_saved_jobs(user_id):
    """
    GET    – return full job objects for all saved job IDs
    POST   – save a job       body: { job_id }
    DELETE – unsave a job     query: ?job_id=<id>
    """
    db     = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT saved_jobs FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"success": False, "error": "User not found."}), 404

    saved = json.loads(row["saved_jobs"]) if row["saved_jobs"] else []

    if request.method == "GET":
        if not saved:
            return jsonify({"success": True, "saved_jobs": [], "count": 0})

        ph = ",".join("?" * len(saved))
        cursor.execute(
            f"""
            SELECT id, job_title, organisation_name, location, org_location,
                   salary, remote_type, experience_level, job_link, company_url,
                   dateposted, job_source
            FROM   jobs WHERE id IN ({ph}) AND is_active = 1
            """,
            saved,
        )
        jobs = [dict(r) for r in cursor.fetchall()]
        return jsonify({"success": True, "saved_jobs": jobs, "count": len(jobs)})

    elif request.method == "POST":
        job_id = str((request.get_json(silent=True) or {}).get("job_id", ""))
        if not job_id:
            return jsonify({"success": False, "error": "job_id required."}), 400
        if job_id not in saved:
            saved.append(job_id)
            cursor.execute(
                "UPDATE users SET saved_jobs = ? WHERE user_id = ?",
                (json.dumps(saved), user_id),
            )
            db.commit()
        return jsonify({"success": True, "saved_jobs": saved, "count": len(saved)})

    elif request.method == "DELETE":
        job_id = str(request.args.get("job_id", ""))
        if job_id in saved:
            saved.remove(job_id)
            cursor.execute(
                "UPDATE users SET saved_jobs = ? WHERE user_id = ?",
                (json.dumps(saved), user_id),
            )
            db.commit()
        return jsonify({"success": True, "saved_jobs": saved, "count": len(saved)})


# ── User Activity ─────────────────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>/activity", methods=["GET"])
def get_user_activity(user_id):
    db     = get_db()
    cursor = db.cursor()
    limit  = request.args.get("limit", 50, type=int)

    cursor.execute(
        """
        SELECT usage_id, date, search_keywords, filters_applied, companies_applied
        FROM   user_usage
        WHERE  user_id = ?
        ORDER  BY date DESC
        LIMIT  ?
        """,
        (user_id, limit),
    )
    activities = [
        {
            "usage_id":          r["usage_id"],
            "date":              r["date"],
            "search_keywords":   r["search_keywords"],
            "filters_applied":   json.loads(r["filters_applied"])   if r["filters_applied"]   else {},
            "companies_applied": json.loads(r["companies_applied"]) if r["companies_applied"] else [],
        }
        for r in cursor.fetchall()
    ]
    return jsonify({"success": True, "count": len(activities), "activities": activities})


@app.route("/api/users/<int:user_id>/apply", methods=["POST"])
def apply_to_job(user_id):
    pass


# ── Site Statistics ───────────────────────────────────────────────────────────

# Simple cache so we don't query 4 count(*) on every homepage load
_stats_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 600  # 10 minutes

@app.route("/api/stats", methods=["GET"])
def get_site_stats():
    """
    Returns total metrics for the homepage counters:
    - Total Jobs Added (active jobs)
    - Total Sponsored Companies 
    - Total Live Domains (assume company_url uniqueness or same as companies)
    - Total Members
    """
    now = datetime.now().timestamp()
    if _stats_cache["data"] and (now - _stats_cache["timestamp"] < CACHE_TTL):
        return jsonify(_stats_cache["data"])

    db = get_db()
    cursor = db.cursor()

    try:
        # Total Active Jobs
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
        total_jobs = cursor.fetchone()[0]

        # Total Sponsored Companies (unique org names mapped to active jobs)
        cursor.execute("SELECT COUNT(DISTINCT organisation_name) FROM jobs")
        total_companies = cursor.fetchone()[0]
        
        # We can simulate Total Live Domains as being equal to companies 
        # or use another query if there's a specific table for domains.
        total_domains = total_companies
        
        # Total Members
        cursor.execute("SELECT COUNT(*) FROM users")
        total_members = cursor.fetchone()[0]

        data = {
            "success": True,
            "stats": {
                "total_jobs": total_jobs,
                "total_companies": total_companies,
                "total_domains": total_domains,  
                "total_members": total_members
            }
        }

        _stats_cache["data"] = data
        _stats_cache["timestamp"] = now

        return jsonify(data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
def track_job_application(user_id):
    """Called when the user clicks 'Apply Now' on job-details.html."""
    data         = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "")

    if not company_name:
        return jsonify({"success": False, "error": "company_name required."}), 400

    db     = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO user_usage (user_id, search_keywords, filters_applied, companies_applied)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            data.get("search_keywords", ""),
            json.dumps(data.get("filters_applied", {})) or None,
            json.dumps([company_name]),
        ),
    )
    db.commit()
    return jsonify({"success": True, "message": "Application tracked."})


@app.route("/api/users/<int:user_id>/search-count", methods=["GET"])
def get_search_count(user_id):
    """
    Returns how many searches the user has done today.
    Free-tier users are capped at 10/day.
    The frontend uses this to show a limit warning banner.
    """
    db     = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS c FROM user_usage
        WHERE  user_id = ? AND date >= date('now', 'start of day')
        """,
        (user_id,),
    )
    count = cursor.fetchone()["c"]

    cursor.execute("SELECT membership_status FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    is_premium = user["membership_status"] == 1
    return jsonify({
        "success":      True,
        "search_count": count,
        "limit":        -1 if is_premium else 10,
        "remaining":    -1 if is_premium else max(0, 10 - count),
        "is_premium":   is_premium,
        "at_limit":     not is_premium and count >= 10,
    })


# ── Invoices ──────────────────────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>/invoices", methods=["GET"])
def get_invoices(user_id):
    """Powers the Invoices panel on dashboard.html."""
    db     = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT payment_id, amount, transaction_id, status, created_at
        FROM   payments
        WHERE  user_id = ?
        ORDER  BY created_at DESC
        """,
        (user_id,),
    )
    invoices = [
        {
            "payment_id":     r["payment_id"],
            "amount":         r["amount"],
            "transaction_id": r["transaction_id"],
            "status":         r["status"],
            "created_at":     r["created_at"],
            "plan":           "Premium Plan",
        }
        for r in cursor.fetchall()
    ]
    return jsonify({"success": True, "invoices": invoices, "count": len(invoices)})


# ── Autocomplete / Suggestions ────────────────────────────────────────────────

@app.route("/api/jobs/suggestions", methods=["GET"])
def get_job_suggestions():
    q = request.args.get("q", "").strip()
    type_param = request.args.get("type", "title") # 'title' or 'location'
    
    if len(q) < 2:
        return jsonify([])
        
    db = get_db()
    cursor = db.cursor()
    
    results = []
    if type_param == "title":
        # Search distinct job titles matching query
        cursor.execute(
            "SELECT DISTINCT job_title FROM jobs WHERE job_title LIKE ? AND is_active = 1 LIMIT 8",
            (f"%{q}%",)
        )
        for row in cursor.fetchall():
            results.append(row["job_title"])
    elif type_param == "location":
        # Search distinct locations matching query
        cursor.execute(
            "SELECT DISTINCT location FROM jobs WHERE location LIKE ? AND is_active = 1 LIMIT 8",
            (f"%{q}%",)
        )
        for row in cursor.fetchall():
            results.append(row["location"])
            
    return jsonify(results)


# ── Job Search ────────────────────────────────────────────────────────────────

@app.route("/api/jobs/search", methods=["GET", "POST"])
@app.route("/api/search",      methods=["GET", "POST"])   # backwards-compat alias
def search_jobs():
    """
    Powers the search forms on index.html and job-listing.html.

    Accepts GET query-params (easy for plain HTML <form action="">) OR POST JSON.

    Parameters
    ──────────
    q / query       keyword / job title  ("Job Title" input)
    location        city or postcode     ("Location" input)
    category        category label       (category <select>)
    remote_type     Full Time | Part Time | Remote | Internship | Contract
    experience_level  Student | Entry | Mid | Senior | Director
    page            1-indexed (default 1)
    limit           results per page (default 10)
    user_id         if provided the search is logged; also enforces free-tier cap
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
    else:
        data = request.args.to_dict()

    query   = (data.get("q") or data.get("query") or data.get("keywords") or "").strip()
    limit   = int(data.get("limit",  10))
    page    = int(data.get("page",    1))
    user_id = data.get("user_id") or session.get("user_id")

    filters = {}
    for key in ("location", "org_location", "remote_type",
                "experience_level", "job_source", "organisation_name", "category"):
        raw_val = data.get(key)
        val = str(raw_val).strip() if raw_val is not None else ""
        if val:
            filters[key] = val

    # ── User Tier Checking ────────────────────────────────────────────────────
    user_tier = 0
    if user_id:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT membership_status FROM users WHERE user_id = ?", (user_id,))
        u = cursor.fetchone()
        if u:
            user_tier = u["membership_status"]
            
        # Optional: rate limiting for free users could go here if still desired, 
        # but the primary lock is the 3-result limit.

    # ── Run search ────────────────────────────────────────────────────────────
    # For higher tiers, we might need more than 200 results from the search engine.
    search_limit = 200
    if user_tier == 1:
        search_limit = 1000
    elif user_tier >= 2:
        search_limit = 3000

    all_results = search_engine.search(
        query=query,
        limit=search_limit,
        filters=filters if filters else None,
        min_score=0.10,
    )

    # ── Location Filter (exists_in_uk / exists_in_london) ────────────────────
    location_filter = (data.get("location_filter") or "").strip()
    if location_filter == "uk":
        all_results = [j for j in all_results if j.get("exists_in_uk") == 1]
    elif location_filter == "london":
        all_results = [j for j in all_results if j.get("exists_in_london") == 1]

    total_actual = len(all_results)
    
    # ── Enforce Limits ────────────────────────────────────────────────────────
    max_allowed = {
        0: 3,
        1: 1000,
        2: 3000,
        3: 1000000
    }.get(user_tier, 3)

    # Slice the results down to the user's tier allowed maximum
    allowed_results = all_results[:max_allowed]
    
    start = (page - 1) * limit
    paged = allowed_results[start: start + limit]

    # ── Log search ────────────────────────────────────────────────────────────
    if user_id and query:
        db     = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO user_usage (user_id, search_keywords, filters_applied) VALUES (?, ?, ?)",
            (user_id, query, json.dumps(filters) if filters else None),
        )
        db.commit()

    jobs = [
        {
            "id":                j["id"],
            "job_title":         j["job_title"],
            "organisation_name": j["organisation_name"],
            "org_location":      j["org_location"],
            "location":          j["location"],
            "remote_type":       j["remote_type"],
            "experience_level":  j["experience_level"],
            "salary":            j["salary"],
            "dateposted":        j["dateposted"],
            "job_description":   j["job_description"],
            "job_link":          j["job_link"],
            "company_url":       j["company_url"],
            "job_source":        j["job_source"],
            "hybrid_score":      float(j["hybrid_score"]) if j.get("hybrid_score") else 0,
            "views_count":       j["views_count"],
            "is_blurred":        False
        }
        for j in paged
    ]
    
    # Inject dummy blurred jobs for Free Users on Page 1 to show them there is more
    if user_tier == 0 and page == 1 and total_actual > 3:
        dummies_to_add = min(limit - len(jobs), total_actual - 3)
        for i in range(dummies_to_add):
            jobs.append({
                "id": f"dummy-{i}",
                "job_title": "Premium Job Listing",
                "organisation_name": "Unlock to View",
                "location": "Hidden",
                "is_blurred": True
            })

    total = len(allowed_results)

    return jsonify({
        "success":     True,
        "count":       len(jobs),
        "total":       total,
        "page":        page,
        "total_pages": max(1, -(-total // limit)),
        "jobs":        jobs,
    })


@app.route("/api/jobs/featured", methods=["GET"])
def get_featured_jobs():
    """Returns recent/featured jobs for the homepage cards on index.html.
    Groups by job_title to avoid showing duplicate listings in the showcase."""
    limit  = request.args.get("limit", 6, type=int)
    db     = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT id, job_title, organisation_name, location, org_location,
               salary, remote_type, experience_level, job_link, company_url,
               dateposted, views_count, exists_in_uk
        FROM   jobs
        WHERE  is_active = 1 AND exists_in_uk = 1
        AND (
            location LIKE '%London%' OR location LIKE '%UK%' 
            OR location LIKE '%United Kingdom%' OR location LIKE '%England%'
            OR location LIKE '%Manchester%' OR location LIKE '%Birmingham%'
            OR location LIKE '%Bristol%' OR location LIKE '%Leeds%'
            OR location LIKE '%Glasgow%' OR location LIKE '%Edinburgh%'
        )
        GROUP  BY job_title
        ORDER  BY dateposted DESC, views_count DESC
        LIMIT  ?
        """,
        (limit,),
    )
    jobs = [dict(r) for r in cursor.fetchall()]
    return jsonify({"success": True, "jobs": jobs, "count": len(jobs)})


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
def get_job_detail(job_id):
    """Returns full job details for job-details.html. Increments view count."""
    db     = get_db()
    cursor = db.cursor()

    cursor.execute("UPDATE jobs SET views_count = views_count + 1 WHERE id = ? AND is_active = 1", (job_id,))
    db.commit()

    cursor.execute("SELECT * FROM jobs WHERE id = ? AND is_active = 1", (job_id,))
    job = cursor.fetchone()
    if not job:
        return jsonify({"success": False, "error": "Job not found."}), 404

    job_data = dict(job)
    job_data.pop("embedding_vector", None)
    job_data.pop("embedding_base64", None)

    uid = session.get("user_id")
    if uid:
        cursor.execute("SELECT saved_jobs FROM users WHERE user_id = ?", (uid,))
        u     = cursor.fetchone()
        saved = json.loads(u["saved_jobs"]) if u and u["saved_jobs"] else []
        job_data["is_saved"] = str(job_id) in saved
    else:
        job_data["is_saved"] = False

    return jsonify({"success": True, "job": job_data})


@app.route("/api/filters", methods=["GET"])
def get_filters():
    """Returns available filter option lists for dropdowns."""
    try:
        return jsonify({"success": True, "filters": search_engine.get_filter_options()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/categories/top", methods=["GET"])
def get_top_categories():
    """Fetch the top 8 job categories dynamically based on active job counts."""
    db     = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT job_category_id, COUNT(*) as count 
        FROM jobs 
        WHERE is_active = 1 AND job_category_id IS NOT NULL 
        GROUP BY job_category_id 
        ORDER BY count DESC 
        LIMIT 8
    """)
    rows = cursor.fetchall()
    
    categories = []
    for r in rows:
        cat_id = r["job_category_id"]
        # Fallback to 'Other'/Briefcase if mapping is missing
        mapping = JOB_CATEGORIES_MAP.get(cat_id, JOB_CATEGORIES_MAP[11])
        categories.append({
            "id": cat_id,
            "name": mapping["name"],
            "icon": mapping["icon"],
            "count": r["count"]
        })

    return jsonify({"success": True, "categories": categories})

# ── Contact Form ──────────────────────────────────────────────────────────────

@app.route("/api/contact", methods=["POST"])
def contact_form():
    """
    Handles the contact-us.html form (id="contactForm").

    contact-form-script.js currently POSTs to assets/php/form-process.php.
    Change that URL to /api/contact (one-line edit in contact-form-script.js).

    The script checks the response text for the word "success", so we
    return plain text "success" on success — not JSON.

    Fields: name, email, msg_subject, phone_number, message, gridCheck
    """
    # Accept both JSON and form-encoded (jQuery $.ajax sends form-encoded)
    data = request.get_json(silent=True) or request.form.to_dict()

    email   = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()
    

    if not email or not message:
        return "error: email and message are required", 400

    # Log it — extend to send email via SMTP if needed
    print(
        f"\n[Contact Form]\n"
        f"  Name:    {data.get('name', '')}\n"
        f"  Email:   {email}\n"
        f"  Subject: {data.get('msg_subject', '')}\n"
        f"  Phone:   {data.get('phone_number', '')}\n"
        f"  Message: {message}\n"
    )

    # contact-form-script.js checks: if (statustxt == "success")
    return "success", 200


# ── Health Check ──────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health_check():

    return jsonify({"success": True, "status": "healthy", "message": "SponsifyUK API is running."})


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SponsifyUK API Server")
    print("  http://localhost:8000")
    print("=" * 60 + "\n")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
    
