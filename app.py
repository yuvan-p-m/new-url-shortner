"""
URL Shortener - Flask Backend
Provides REST API for shortening URLs and redirecting short codes.
"""

import sqlite3
import random
import string
import re
from datetime import datetime
from flask import Flask, request, jsonify, redirect, render_template, g

app = Flask(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
DATABASE = "database.db"
BASE_URL = "http://localhost:5000"
SHORT_CODE_LENGTH = 6  # Generate 6-character codes by default


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    """Return a database connection, reusing it within a request context."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # rows behave like dicts
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection at the end of each request."""
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    """Create the urls table if it doesn't already exist."""
    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT    NOT NULL,
                short_code   TEXT    UNIQUE NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()


# ── Utility functions ─────────────────────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    """
    Validate that the given string is a well-formed http/https URL.
    Uses a lightweight regex; no DNS look-up is performed.
    """
    pattern = re.compile(
        r"^(https?://)?"                        # scheme (optional but required below)
        r"(([A-Za-z0-9\-]+\.)+[A-Za-z]{2,})"   # domain
        r"(:\d+)?"                               # optional port
        r"(/[^\s]*)?"                            # optional path
        r"(\?[^\s]*)?"                           # optional query
        r"(#[^\s]*)?$",                          # optional fragment
        re.IGNORECASE,
    )
    return bool(pattern.match(url)) and url.startswith(("http://", "https://"))


def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    """Return a random alphanumeric string of the given length."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def unique_short_code() -> str:
    """
    Generate a short code that does not already exist in the database.
    Tries up to 10 times before giving up.
    """
    db = get_db()
    for _ in range(10):
        code = generate_short_code()
        existing = db.execute(
            "SELECT id FROM urls WHERE short_code = ?", (code,)
        ).fetchone()
        if not existing:
            return code
    raise RuntimeError("Unable to generate a unique short code. Please try again.")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the frontend single-page app."""
    return render_template("index.html")


@app.route("/shorten", methods=["POST"])
def shorten():
    """
    POST /shorten
    Body: { "url": "https://example.com/very/long/url" }

    Returns:
        201 – { "short_url": "...", "code": "...", "created_at": "..." }
        200 – same payload when the URL was already shortened (de-dup)
        400 – { "error": "<message>" }
    """
    data = request.get_json(silent=True)

    # ── Validate request body ──
    if not data or "url" not in data:
        return jsonify({"error": "Request body must be JSON with a 'url' field."}), 400

    original_url = data["url"].strip()

    if not original_url:
        return jsonify({"error": "URL must not be empty."}), 400

    if not is_valid_url(original_url):
        return jsonify(
            {"error": "Invalid URL. Please include the scheme (http:// or https://)."}
        ), 400

    db = get_db()

    # ── De-duplicate: return existing code if URL already stored ──
    row = db.execute(
        "SELECT short_code, created_at FROM urls WHERE original_url = ?",
        (original_url,),
    ).fetchone()

    if row:
        code = row["short_code"]
        return jsonify({
            "short_url": f"{BASE_URL}/{code}",
            "code": code,
            "created_at": row["created_at"],
            "already_existed": True,
        }), 200

    # ── Create new entry ──
    code = unique_short_code()
    now = datetime.utcnow().isoformat(timespec="seconds")

    db.execute(
        "INSERT INTO urls (original_url, short_code, created_at) VALUES (?, ?, ?)",
        (original_url, code, now),
    )
    db.commit()

    return jsonify({
        "short_url": f"{BASE_URL}/{code}",
        "code": code,
        "created_at": now,
        "already_existed": False,
    }), 201


@app.route("/<short_code>")
def redirect_to_url(short_code):
    """
    GET /<short_code>
    Redirects the browser to the original URL (HTTP 302).
    Returns 404 JSON if the short code is unknown.
    """
    # Basic sanity check – codes are alphanumeric only
    if not re.match(r"^[A-Za-z0-9]{4,12}$", short_code):
        return jsonify({"error": "Invalid short code format."}), 404

    db = get_db()
    row = db.execute(
        "SELECT original_url FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()

    if row is None:
        return jsonify({"error": f"Short code '{short_code}' not found."}), 404

    return redirect(row["original_url"], code=302)


@app.route("/api/stats/<short_code>", methods=["GET"])
def stats(short_code):
    """
    GET /api/stats/<short_code>
    Returns metadata for a short code (original URL, creation time).
    """
    db = get_db()
    row = db.execute(
        "SELECT original_url, short_code, created_at FROM urls WHERE short_code = ?",
        (short_code,),
    ).fetchone()

    if row is None:
        return jsonify({"error": f"Short code '{short_code}' not found."}), 404

    return jsonify({
        "short_url": f"{BASE_URL}/{row['short_code']}",
        "original_url": row["original_url"],
        "code": row["short_code"],
        "created_at": row["created_at"],
    }), 200


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
