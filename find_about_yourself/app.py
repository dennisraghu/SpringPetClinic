"""
Find out about yourself — Flask UI with SQLite storage.
"""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

# App owner (fixed data served by /api/owner)
APP_OWNER_NAME = "Darth Vader"
APP_OWNER_RESIDENCE = "Hollywood"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = os.environ.get("FIND_ABOUT_DB", str(BASE_DIR / "profiles.sqlite"))


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(get_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS self_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                address TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_self_profiles_name ON self_profiles (name)")
        conn.commit()


def validate_profile(name: str, age_raw: str, address: str):
    errors = []
    name = (name or "").strip()
    address = (address or "").strip()
    if not name:
        errors.append("Name is required.")
    if not address:
        errors.append("Address is required.")
    age = None
    if not (age_raw or "").strip():
        errors.append("Age is required.")
    else:
        try:
            age = int(age_raw.strip())
            if age < 0 or age > 150:
                errors.append("Age must be between 0 and 150.")
        except ValueError:
            errors.append("Age must be a whole number.")
    return errors, name, age, address


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me-in-production")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/save", methods=["POST"])
def save():
    name = request.form.get("name", "")
    age_raw = request.form.get("age", "")
    address = request.form.get("address", "")
    errors, name, age, address = validate_profile(name, age_raw, address)
    if errors:
        for e in errors:
            flash(e, "error")
        return render_template(
            "index.html",
            form_name=name,
            form_age=age_raw,
            form_address=address,
        )
    with closing(get_connection()) as conn:
        conn.execute(
            "INSERT INTO self_profiles (name, age, address) VALUES (?, ?, ?)",
            (name, age, address),
        )
        conn.commit()
    flash("Saved your details.", "success")
    return redirect(url_for("index"))


@app.route("/api/owner", methods=["GET"])
def api_owner():
    return jsonify(
        {
            "name": APP_OWNER_NAME,
            "residence": APP_OWNER_RESIDENCE,
        }
    )


@app.route("/search", methods=["GET"])
def search():
    q = (request.args.get("name") or "").strip()
    if not q:
        return render_template(
            "index.html",
            search_performed=True,
            found=None,
            search_query="",
        )
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT name, age, address FROM self_profiles
            WHERE lower(name) = lower(?)
            ORDER BY id ASC
            LIMIT 1
            """,
            (q,),
        ).fetchone()
    found = dict(row) if row else None
    return render_template(
        "index.html",
        search_performed=True,
        found=found,
        search_query=q,
    )


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
