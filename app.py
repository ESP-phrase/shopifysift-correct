"""
Flask dashboard for the GitHub keyword scraper.

Routes:
    GET  /              — redirect to dashboard or login
    GET  /login         — login form
    POST /login         — authenticate
    POST /logout        — clear session
    GET  /dashboard     — search form + recent results
    POST /scrape        — kick off a scrape job (background thread)
    GET  /api/jobs      — list jobs (for polling)
    GET  /api/repos     — list repos for a job

Run:
    python app.py            # dev (Flask debug)
    waitress-serve --host=0.0.0.0 --port=8000 app:app   # production
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from scraper import scrape, Repo


load_dotenv()

HERE = Path(__file__).parent
DB_PATH = HERE / "scraper.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ---- db --------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query       TEXT NOT NULL,
    max_pages   INTEGER NOT NULL,
    status      TEXT NOT NULL,        -- queued | running | done | error
    error       TEXT,
    started_at  REAL,
    finished_at REAL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS repos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    full_name   TEXT NOT NULL,
    url         TEXT NOT NULL,
    description TEXT,
    language    TEXT,
    stars       INTEGER,
    updated     TEXT,
    found_at    REAL NOT NULL,
    UNIQUE(job_id, full_name)
);

CREATE INDEX IF NOT EXISTS idx_repos_job_id ON repos(job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


# ---- auth ------------------------------------------------------------------

def _expected_creds() -> tuple[str, str]:
    return (
        os.environ.get("DASH_USER", "admin"),
        os.environ.get("DASH_PASS", "admin"),
    )


def login_required(f):
    from functools import wraps

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            if request.path.startswith("/api/"):
                abort(401)
            return redirect(url_for("login_view", next=request.path))
        return f(*args, **kwargs)

    return wrapped


# ---- jobs (background scraping) -------------------------------------------

# A thread-safe write helper. Each background thread opens its own sqlite
# connection (sqlite connections aren't shareable across threads).
def _db_write(query: str, params: tuple = ()):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid


def _run_job(job_id: int, query: str, max_pages: int) -> None:
    started = time.time()
    _db_write(
        "UPDATE jobs SET status='running', started_at=? WHERE id=?",
        (started, job_id),
    )

    def on_result(r: Repo) -> None:
        try:
            with closing(sqlite3.connect(DB_PATH)) as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO repos
                       (job_id, full_name, url, description, language, stars, updated, found_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        job_id,
                        r.full_name,
                        r.url,
                        r.description,
                        r.language,
                        r.stars,
                        r.updated,
                        time.time(),
                    ),
                )
                conn.commit()
        except Exception as e:
            print(f"[job {job_id}] insert failed: {e}")

    try:
        scrape(query, max_pages=max_pages, headless=True, on_result=on_result)
        _db_write(
            "UPDATE jobs SET status='done', finished_at=? WHERE id=?",
            (time.time(), job_id),
        )
    except Exception as e:
        _db_write(
            "UPDATE jobs SET status='error', error=?, finished_at=? WHERE id=?",
            (str(e)[:500], time.time(), job_id),
        )


# ---- routes ----------------------------------------------------------------

@app.route("/")
def index():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_view"))


@app.route("/login", methods=["GET", "POST"])
def login_view():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        eu, ep = _expected_creds()
        if u == eu and p == ep:
            session["user"] = u
            return redirect(request.args.get("next") or url_for("dashboard"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login_view"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    jobs = db.execute(
        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    return render_template("dashboard.html", jobs=jobs, user=session["user"])


@app.route("/scrape", methods=["POST"])
@login_required
def scrape_view():
    query = (request.form.get("query") or "").strip()
    if not query:
        return redirect(url_for("dashboard"))
    try:
        max_pages = int(request.form.get("max_pages", 3))
    except ValueError:
        max_pages = 3
    max_pages = max(1, min(max_pages, 10))

    job_id = _db_write(
        "INSERT INTO jobs (query, max_pages, status, created_at) VALUES (?, ?, 'queued', ?)",
        (query, max_pages, time.time()),
    )

    t = threading.Thread(target=_run_job, args=(job_id, query, max_pages), daemon=True)
    t.start()
    return redirect(url_for("dashboard"))


@app.route("/api/jobs")
@login_required
def api_jobs():
    db = get_db()
    rows = db.execute(
        """SELECT j.*, COUNT(r.id) AS repo_count
           FROM jobs j LEFT JOIN repos r ON r.job_id = j.id
           GROUP BY j.id ORDER BY j.created_at DESC LIMIT 20"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/repos")
@login_required
def api_repos():
    job_id = request.args.get("job_id", type=int)
    db = get_db()
    if job_id:
        rows = db.execute(
            "SELECT * FROM repos WHERE job_id=? ORDER BY stars DESC NULLS LAST, found_at DESC",
            (job_id,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM repos ORDER BY found_at DESC LIMIT 100"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


# ---- entrypoint ------------------------------------------------------------

init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="127.0.0.1", port=port, debug=True)
