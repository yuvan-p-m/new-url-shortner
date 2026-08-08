# [snip] — URL Shortener

A minimal, clean URL shortener built with **Python Flask** + **SQLite**.
Paste a long URL, get a short one instantly. No external services required.

---

## Project Structure

```
url_shortener/
├── app.py               # Flask application (routes, DB helpers, validation)
├── database.db          # SQLite database (auto-created on first run)
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html       # Single-page frontend
├── static/
│   ├── style.css        # Styling (Space Grotesk + terminal aesthetic)
│   └── script.js        # Fetch API, clipboard, session history
└── README.md
```

---

## Quick Start

### 1. Prerequisites

- Python 3.9 or newer
- pip

### 2. Clone / download the project

```bash
git clone https://github.com/yourname/url-shortener.git
cd url_shortener
```

### 3. Create and activate a virtual environment (recommended)

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python app.py
```

Flask will start in debug mode:

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### 6. Open the browser

Navigate to **http://localhost:5000** — the frontend is served automatically.

---

## Database

SQLite creates `database.db` automatically on the first request.
The schema is:

```sql
CREATE TABLE urls (
    id           INTEGER   PRIMARY KEY AUTOINCREMENT,
    original_url TEXT      NOT NULL,
    short_code   TEXT      UNIQUE NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

To inspect the database directly:

```bash
sqlite3 database.db
sqlite> SELECT * FROM urls;
sqlite> .quit
```

---

## REST API Reference

### POST /shorten

Shorten a URL. Returns the existing short code if the URL was already shortened.

**Request**

```http
POST /shorten
Content-Type: application/json

{
  "url": "https://example.com/very/long/path?foo=bar"
}
```

**Response — 201 Created (new entry)**

```json
{
  "short_url":      "http://localhost:5000/aB3xYz",
  "code":           "aB3xYz",
  "created_at":     "2024-06-15T10:42:00",
  "already_existed": false
}
```

**Response — 200 OK (duplicate URL)**

```json
{
  "short_url":      "http://localhost:5000/aB3xYz",
  "code":           "aB3xYz",
  "created_at":     "2024-06-15T10:42:00",
  "already_existed": true
}
```

**Response — 400 Bad Request**

```json
{ "error": "Invalid URL. Please include the scheme (http:// or https://)." }
```

---

### GET /<short_code>

Redirect to the original URL.

```http
GET /aB3xYz
```

- **302 Found** — redirects to the original URL
- **404 Not Found** — `{ "error": "Short code 'aB3xYz' not found." }`

---

### GET /api/stats/<short_code>

Fetch metadata for a short code without redirecting.

```http
GET /api/stats/aB3xYz
```

**Response — 200 OK**

```json
{
  "short_url":    "http://localhost:5000/aB3xYz",
  "original_url": "https://example.com/very/long/path?foo=bar",
  "code":         "aB3xYz",
  "created_at":   "2024-06-15T10:42:00"
}
```

---

## Testing with curl

```bash
# Shorten a URL
curl -s -X POST http://localhost:5000/shorten \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/some/long/path?a=1&b=2"}' | python3 -m json.tool

# Shorten the same URL again (returns existing code)
curl -s -X POST http://localhost:5000/shorten \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/some/long/path?a=1&b=2"}' | python3 -m json.tool

# Follow the redirect (-L flag)
curl -L http://localhost:5000/aB3xYz

# Look up stats without redirecting
curl -s http://localhost:5000/api/stats/aB3xYz | python3 -m json.tool

# Test invalid URL
curl -s -X POST http://localhost:5000/shorten \
     -H "Content-Type: application/json" \
     -d '{"url": "not-a-url"}' | python3 -m json.tool

# Test missing body
curl -s -X POST http://localhost:5000/shorten \
     -H "Content-Type: application/json" \
     -d '{}' | python3 -m json.tool
```

---

## Testing with Postman

1. Open Postman and create a new **Collection** called "Snip – URL Shortener".

2. **Shorten a URL**
   - Method: `POST`
   - URL: `http://localhost:5000/shorten`
   - Tab **Body → raw → JSON**:
     ```json
     { "url": "https://www.wikipedia.org/wiki/URL_shortening" }
     ```
   - Click **Send**. Expect `201 Created`.

3. **Redirect test**
   - Method: `GET`
   - URL: `http://localhost:5000/<code>` (replace `<code>` from step 2)
   - Under **Settings**, turn **Follow redirects** OFF to see the `302` response.
   - Turn it ON to be redirected to Wikipedia.

4. **Stats lookup**
   - Method: `GET`
   - URL: `http://localhost:5000/api/stats/<code>`
   - Expect `200 OK` with the metadata JSON.

5. **Error handling**
   - Repeat step 2 with `"url": "ftp://not-http.example.com"`.
   - Expect `400 Bad Request` with an error message.

---

## Configuration

To change the base URL (e.g. for deployment), edit `app.py`:

```python
BASE_URL = "https://your-domain.com"   # line 13
```

To adjust the short code length (6–8 characters recommended):

```python
SHORT_CODE_LENGTH = 8   # line 14
```

---

## Running in Production

For production, replace the built-in dev server with **Gunicorn**:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
```

> **Note:** Call `init_db()` once before starting workers, or add it to an
> application factory, to avoid race conditions on database creation.
