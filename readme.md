# File & JSON Manager

**A lightweight local service to upload/download files and convert JSON into simple SQL/document databases.**

This repository contains a Streamlit frontend (`app.py`), a Flask backend (`backend.py`) and supporting modules (`backend_core.py`, `classifier.py`, small user-management helper). The system provides:

- Upload of regular files (images, audio, video, PDFs, docs) with automatic categorization and UUID indexing.
- Upload of JSON (file or pasted text) which the backend heuristically classifies as SQL-like or document-like and creates either a SQLite DB or a JSON snapshot. A fresh username/password pair is generated and returned for each JSON-created DB.
- Download endpoint to retrieve uploaded files or user-created DBs (authorization required for private DBs).
- Simple token-based auth used by the Streamlit frontend (token format: `username:uuid`).

---

## Table of contents

- [Quick start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation & run](#installation--run)
- [Project layout](#project-layout)
- [How it works (high level)](#how-it-works-high-level)
- [API reference (examples)](#api-reference-examples)
- [Authentication & tokens](#authentication--tokens)
- [File & JSON handling details](#file--json-handling-details)
- [Indexing & storage layout](#indexing--storage-layout)
- [Classifier behavior](#classifier-behavior)
- [Testing & debugging tips](#testing--debugging-tips)
- [Security & caveats](#security--caveats)
- [Contributing](#contributing)
- [License](#license)

---

## Quick start

1. Create a user (see `users_helper.py` usage at bottom of repository):

```bash
python users_helper.py
# follow prompts to create a username and password
```

2. Start the backend (default listens on port 8000):

```bash
python backend.py
```

3. Start the Streamlit frontend (defaults to `http://localhost:8501`):

```bash
streamlit run app.py
```

Open the Streamlit UI in your browser, login with the user created in step 1, and start uploading files or JSON.

---

## Prerequisites

- Python 3.8+
- `pip` (or virtualenv/venv)

Recommended (install into a virtual environment):

```bash
pip install -r requirements.txt
```

If you don't have a `requirements.txt`, install the minimal packages:

```bash
pip install flask streamlit requests passlib python-magic werkzeug
```

Notes:
- `python-magic` is optional but improves file-type detection in `classifier.py`.
- `passlib` is used for password hashing.

---

## Installation & run

1. Clone the repo and `cd` into it.
2. (Optional) Create a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
```

3. Create a first user:

```bash
python users_helper.py
```

4. Run backend:

```bash
python backend.py
```

5. Run the frontend (in another terminal):

```bash
streamlit run app.py
```

---

## Project layout

```
.
├─ app.py                # Streamlit frontend
├─ backend.py            # Flask backend
├─ backend_core.py       # core helpers, DB creation, indexing
├─ classifier.py         # file-type heuristics and save logic
├─ users_helper.py       # tiny script to add users to users.json
├─ users.json            # password-hash store (auto-created)
├─ db_index.json         # index mapping uuids/usernames -> stored file/db metadata
├─ categorized_data/     # saved non-json files (Images, Videos, Audio, Documents, Others)
├─ user_dbs/             # created sqlite DB files for SQL-like JSON uploads
├─ user_docs/            # created JSON snapshot files for document-like JSON uploads
└─ temp_upload/          # temporary upload backup location
```

---

## How it works (high level)

- The Streamlit app provides a login screen and two upload flows: non-JSON files, and JSON (file or pasted text).
- When a normal file is uploaded the backend saves the file (either via `classifier.classify_and_save` if available, or by mimetype/extension heuristics) under `categorized_data/<Category>/` and returns a generated UUID.
- When a JSON file or JSON text is uploaded, `backend_core.detect_sql` heuristically determines whether the data is SQL-like (a list of uniform objects with primitive fields) or document-like. A new username/password pair is generated and stored in `users.json`. If SQL-like a SQLite DB is created in `user_dbs/`; otherwise the JSON is saved under `user_docs/`. The new username is saved in the global `db_index.json` for downloads.
- Downloading requires a code (either the file uuid or the auto-generated username for a JSON-created DB). DB downloads are restricted to the DB owner.

---

## API reference (examples)

### Login

```
POST /login
Content-Type: application/json
{
  "username": "alice",
  "password": "secret"
}

Response:
{ "success": true, "token": "alice:4f2a..." }
```

Use the returned `token` as the `Authorization` header for subsequent calls from the frontend.

### Upload file (multipart form)

```
POST /upload
Headers: Authorization: <token>
Form field: file -> binary file (the frontend sends this automatically)
```

Success response (non-JSON file):

```json
{ "success": true, "type": "images", "uuid": "<generated-uuid>" }
```

If the backend suspects uploaded file was JSON (filename `.json`), it will analyse and return credentials:

```json
{ "success": true, "type": "sql", "username": "user_xxx", "password": "Ab3...", "reason": "Decided SQL-like..." }
```

### Upload JSON as text

```
POST /upload
Form field: text_json -> raw JSON text
```

Same response behavior as JSON file flow.

### Download

```
GET /download/<code>
Headers: Authorization: <token>  # optional for regular files but required for private DBs
```

If `<code>` maps to a file UUID you'll receive the file as an attachment. If it maps to a username/DB, only the DB owner (token username) can download the DB.

---

## Authentication & tokens

- Passwords are stored as PBKDF2-SHA256 hashes using `passlib`.
- `verify_token` in `backend.py` simply checks that the left-hand-side of a token (`username:...`) exists in `users.json`. The token itself is not cryptographically verified beyond that — it is a simple convenience format used by the frontend.
- **Caveat:** Current token handling is intentionally simple for a local/small deployment. For production use, replace with JWTs or another robust token/session management approach and protect all endpoints with TLS.

---

## File & JSON handling details

- **Regular files:** saved under `categorized_data/<Category>/<uuid><ext>` with `Category` chosen by `classifier.py` (Images, Videos, Audio, Documents, Others).
- **JSON uploads:**
  - If `detect_sql` returns `True` the JSON list-of-objects is written into a SQLite DB table named `data` inside `user_dbs/<username>.db`. Lists/dicts inside fields are serialized as JSON text inside TEXT columns.
  - If `detect_sql` returns `False` the entire JSON snapshot is saved to `user_docs/<username>.json`.
  - A new account (username/password) is generated and stored in `users.json` for each JSON upload so that the created DB can be downloaded later by that owner.

---

## Indexing & storage layout

- `db_index.json` maps keys (file UUIDs **and** owner usernames for JSON-created DBs) to metadata objects like:

```json
{
  "<uuid_or_username>": {
    "type": "images|videos|audio|documents|sql|doc",
    "owner": "username or 'anonymous'",
    "path": "path/to/file",
    "original_name": "original filename",
    "created_at": "UTC ISO timestamp"
  }
}
```

This file is updated atomically via the helper `_write_index_entry`.

---

## Classifier behavior

- `classifier.classify_and_save` tries to use `python-magic` to detect mime type from bytes. If not available, it falls back to extension and simple byte-pattern heuristics (e.g., `%PDF` for PDF, `JFIF` or JPEG magic, text heuristic).
- If `classifier` is importable it is used by `backend_core.save_regular_file`. Otherwise a simple mimetype-based fallback is used.

---

## Testing & debugging tips

- If uploads appear to hang, check both Streamlit logs and Flask logs for stack traces. The Flask server by default prints exceptions when run with `debug=True`.
- `users.json` and `db_index.json` are created automatically; if corrupted remove or restore from backup.
- Use `curl` for quick tests:

```bash
# login
curl -s -X POST http://localhost:8000/login -H 'Content-Type: application/json' -d '{"username":"alice","password":"secret"}'

# upload JSON text
curl -s -X POST http://localhost:8000/upload -F 'text_json={"a":1,"b":2}'

# upload file
curl -s -X POST http://localhost:8000/upload -F 'file=@/path/to/photo.jpg'
```

---

## Security & caveats

This project is built as a local/dev tool and includes several simplifications:

- Token handling is naive (format `username:uuid`) and not safe for public deployments.
- Uploaded files and DBs are stored on disk with no encryption.
- There is no rate limiting, input-size throttling, or advanced validation for untrusted JSON.
- `detected_sql` heuristic is best-effort and may misclassify complex data.

**Recommendations before deploying publicly:**
- Use HTTPS and proper session tokens (JWT/OAuth2) instead of the simple token format.
- Add size limits, virus scanning, and storage quotas.
- Harden `users.json` storage and consider using a proper database for users and index.

---

## Contributing

Contributions and fixes are welcome. Suggested next steps:

- Add unit tests for `detect_sql` (edge cases, nested structures).
- Improve token/session management and add role-based access.
- Add optional S3/local hybrid storage backend.
- Add pagination / query UI for created DBs in the Streamlit app.

---

## License

This project is released under the MIT License. See `LICENSE` (add one if you want explicit license text).

---

If you'd like, I can also:
- Add a `requirements.txt` and/or `Dockerfile` to containerize the app.
- Produce a quick `systemd` unit or `docker-compose.yml` for easy local deployments.
- Generate example `curl` commands with realistic tokens and sample JSON.

Tell me which extra artifacts you'd like and I will add them.

