"""
ShopifySift dashboard — login-gated UI for the GitHub scraper.

Credentials come from env vars (defaults shown):
    SHOPIFYSIFT_USER  (default: admin)
    SHOPIFYSIFT_PASS  (default: admin — change me!)
    SHOPIFYSIFT_SECRET (session signing; auto-generated if absent)

Run:
    python dashboard.py
    python dashboard.py --csv leads.csv --port 3010
"""

import argparse
import csv
import os
import secrets
import subprocess
import sys
from collections import Counter
from functools import wraps
from pathlib import Path

from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for,
)


HERE = Path(__file__).parent

app = Flask(__name__)
app.config["CSV_PATH"] = HERE / "results.csv"
app.config["USERNAME"] = os.environ.get("SHOPIFYSIFT_USER", "admin")
app.config["PASSWORD"] = os.environ.get("SHOPIFYSIFT_PASS", "admin")
app.secret_key = os.environ.get("SHOPIFYSIFT_SECRET") or secrets.token_hex(32)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "unauthorized"}), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def load_rows() -> list[dict]:
    path: Path = app.config["CSV_PATH"]
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        if u == app.config["USERNAME"] and p == app.config["PASSWORD"]:
            session["user"] = u
            session.permanent = bool(request.form.get("remember"))
            nxt = request.args.get("next") or url_for("index")
            return redirect(nxt)
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    rows = load_rows()
    by_query = Counter(r["query"] for r in rows)
    by_repo = Counter(r["repo"] for r in rows)
    queries = sorted(by_query.keys())
    return render_template(
        "index.html",
        rows=rows,
        total=len(rows),
        unique_repos=len(by_repo),
        queries=queries,
        top_queries=by_query.most_common(10),
        top_repos=by_repo.most_common(10),
        csv_path=str(app.config["CSV_PATH"]),
        user=session.get("user"),
    )


@app.route("/api/rows")
@login_required
def api_rows():
    rows = load_rows()
    q = request.args.get("q", "").lower()
    repo = request.args.get("repo", "").lower()
    path_q = request.args.get("path", "").lower()

    def match(r):
        if q and q not in r["query"].lower():
            return False
        if repo and repo not in r["repo"].lower():
            return False
        if path_q and path_q not in r["path"].lower():
            return False
        return True

    return jsonify([r for r in rows if match(r)])


@app.route("/api/run", methods=["POST"])
@login_required
def api_run():
    data = request.get_json(silent=True) or {}
    queries = [q.strip() for q in (data.get("queries") or []) if q.strip()]
    if not queries:
        return jsonify({"ok": False, "error": "no queries"}), 400

    cmd = [sys.executable, str(HERE / "scraper.py"), *queries]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, cwd=str(HERE),
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "timed out after 10 min"}), 504

    return jsonify({
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-2000:],
    })


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=str(HERE / "results.csv"))
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--host", default="127.0.0.1")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app.config["CSV_PATH"] = Path(args.csv)
    print(f"reading {app.config['CSV_PATH']}")
    print(f"login: {app.config['USERNAME']} / {'*' * len(app.config['PASSWORD'])}")
    print(f"http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
