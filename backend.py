# backend.py
from flask import Flask, request, jsonify, send_file
import json
import os
import uuid
from passlib.hash import pbkdf2_sha256
import mimetypes
import sqlite3

from backend_core import (
    detect_sql,
    create_sql_db,
    create_doc_db,
    save_regular_file,
    DB_INDEX
)

app = Flask(__name__)

USERS_JSON = "users.json"

# Ensure users store
if not os.path.exists(USERS_JSON):
    with open(USERS_JSON, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4)

# Ensure DB index
if not os.path.exists(DB_INDEX):
    with open(DB_INDEX, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4)


# -------------------------------
# AUTH HELPERS
# -------------------------------
def generate_token(username):
    return f"{username}:{uuid.uuid4().hex}"


def verify_token(token):
    if not token or ":" not in token:
        return None
    username = token.split(":", 1)[0]
    with open(USERS_JSON, "r", encoding="utf-8") as f:
        users = json.load(f)
    return username if username in users else None


# -------------------------------
# LOGIN
# -------------------------------
@app.post("/login")
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "username/password required"}), 400

    with open(USERS_JSON, "r", encoding="utf-8") as f:
        users = json.load(f)

    if username not in users:
        return jsonify({"success": False, "error": "Invalid login"}), 401

    if not pbkdf2_sha256.verify(password, users[username]):
        return jsonify({"success": False, "error": "Invalid login"}), 401

    token = generate_token(username)
    return jsonify({"success": True, "token": token})


# -------------------------------
# UPLOAD (JSON + FILES)
# -------------------------------
@app.post("/upload")
def upload():
    token = request.headers.get("Authorization")
    username = verify_token(token)
    if not username:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    # If file upload
    if "file" in request.files:
        f = request.files["file"]
        os.makedirs("temp_upload", exist_ok=True)
        temp_path = os.path.join("temp_upload", f.filename)
        f.save(temp_path)

        # -------- JSON file case --------
        if f.filename.lower().endswith(".json"):
            try:
                with open(temp_path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except Exception:
                return jsonify({"success": False, "error": "Invalid JSON"}), 400

            # Normalize for SQL detection
            if isinstance(data, dict):
                rows = [data]
            elif isinstance(data, list):
                rows = data
            else:
                return jsonify({"success": False, "error": "JSON must be dict or list"}), 400

            is_sql, reason = detect_sql(rows)

            if is_sql:
                db_uuid, db_path = create_sql_db(username, rows)
                return jsonify({"success": True, "type": "sql", "uuid": db_uuid, "reason": reason})

            else:
                db_uuid, db_path = create_doc_db(username, data)
                return jsonify({"success": True, "type": "doc", "uuid": db_uuid, "reason": reason})

        # -------- Regular file case (images/videos/pdf/etc.) --------
        with open(temp_path, "rb") as rb:
            file_bytes = rb.read()

        file_uuid, category, stored_path = save_regular_file(
            temp_path, username, original_name=f.filename, data_bytes=file_bytes
        )

        return jsonify({
            "success": True,
            "type": category,
            "uuid": file_uuid
        })

    # TEXT JSON input
    txt = request.form.get("text_json")
    if txt:
        try:
            obj = json.loads(txt)
        except:
            return jsonify({"success": False, "error": "Invalid JSON text"}), 400

        rows = obj if isinstance(obj, list) else [obj]

        is_sql, reason = detect_sql(rows)

        if is_sql:
            db_uuid, db_path = create_sql_db(username, rows)
            return jsonify({"success": True, "type": "sql", "uuid": db_uuid, "reason": reason})

        else:
            db_uuid, db_path = create_doc_db(username, obj)
            return jsonify({"success": True, "type": "doc", "uuid": db_uuid, "reason": reason})

    return jsonify({"success": False, "error": "No input provided"}), 400


# -------------------------------
# DOWNLOAD (FINAL FIX — RETURNS ORIGINAL FILE WITHOUT CORRUPTION)
# -------------------------------
@app.get("/download/<uuid_code>")
def download(uuid_code):
    token = request.headers.get("Authorization")
    username = verify_token(token)
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    with open(DB_INDEX, "r", encoding="utf-8") as f:
        index = json.load(f)

    if uuid_code not in index:
        return jsonify({"error": "UUID not found"}), 404

    entry = index[uuid_code]
    if entry.get("owner") != username:
        return jsonify({"error": "Access denied"}), 403

    file_path = entry.get("path")
    original_name = entry.get("original_name", os.path.basename(file_path))

    if not os.path.exists(file_path):
        return jsonify({"error": "File missing"}), 404

    # ---- FIX: Serve binary file exactly as stored ----
    mime, _ = mimetypes.guess_type(original_name)
    if not mime:
        mime = "application/octet-stream"

    return send_file(
        file_path,
        mimetype=mime,
        as_attachment=True,
        download_name=original_name
    )


# -------------------------------
# SHOW DB CONTENT
# -------------------------------
@app.get("/show_db/<uuid_code>")
def show_db(uuid_code):
    token = request.headers.get("Authorization")
    username = verify_token(token)
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    with open(DB_INDEX, "r") as f:
        index = json.load(f)

    if uuid_code not in index:
        return jsonify({"error": "UUID not found"}), 404

    entry = index[uuid_code]

    if entry["owner"] != username:
        return jsonify({"error": "Access denied"}), 403

    if entry["type"] == "sql":
        conn = sqlite3.connect(entry["path"])
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]

        data = {}
        for t in tables:
            cur.execute(f"SELECT * FROM {t}")
            rows = cur.fetchall()
            cur.execute(f"PRAGMA table_info({t})")
            cols = [c[1] for c in cur.fetchall()]
            data[t] = {"columns": cols, "rows": rows}

        conn.close()
        return jsonify({"type": "sql", "data": data})

    else:
        with open(entry["path"], "r", encoding="utf-8") as fp:
            return jsonify({"type": "doc", "data": json.load(fp)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
