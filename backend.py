"""
backend.py - Flask backend
Run on your laptop:
    python backend.py

Uploads stored at:
    uploads/<username>/<FileType>/<uuid>.<ext>

Files indexed at:
    file_index.json

Users stored at:
    users.json  (created using create_user.py)
Sessions stored at:
    sessions.json
"""

import os
import json
import uuid
import time
from pathlib import Path

from flask import Flask, request, send_file, jsonify
from passlib.hash import pbkdf2_sha256
from werkzeug.utils import secure_filename

from classifier import detect_filetype

app = Flask(__name__)

# ---------------------------
# Paths
# ---------------------------
USERS_FILE = "users.json"
INDEX_FILE = "file_index.json"
SESSIONS_FILE = "sessions.json"
UPLOADS_DIR = "uploads"

# ---------------------------
# JSON Helpers
# ---------------------------
def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ---------------------------
# Auth Helpers
# ---------------------------
def verify_user(username, password):
    users = load_json(USERS_FILE)
    if username not in users:
        return False
    try:
        return pbkdf2_sha256.verify(password, users[username])
    except Exception:
        return False

def create_session(username):
    sessions = load_json(SESSIONS_FILE)
    token = str(uuid.uuid4())
    sessions[token] = {
        "username": username,
        "created_at": int(time.time())
    }
    save_json(SESSIONS_FILE, sessions)
    return token

def get_username_from_token(token):
    if not token:
        return None
    sessions = load_json(SESSIONS_FILE)
    return sessions.get(token, {}).get("username")

# ---------------------------
# Init folders
# ---------------------------
Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)

# ===========================
#         ROUTES
# ===========================

# ---------------------------
# LOGIN
# ---------------------------
@app.post("/login")
def login():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "msg": "Missing credentials"}), 400

    if verify_user(username, password):
        token = create_session(username)
        return jsonify({"success": True, "token": token})

    return jsonify({"success": False, "msg": "Invalid credentials"}), 401

# ---------------------------
# UPLOAD
# ---------------------------
@app.post("/upload")
def upload():
    token = request.headers.get("Authorization")
    username = get_username_from_token(token)

    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Get original extension
    orig_name = secure_filename(f.filename)
    _, ext = os.path.splitext(orig_name)
    ext = ext.lower()

    # Save temp file
    tmp_name = f"tmp_{uuid.uuid4().hex}{ext}"
    tmp_path = Path(tmp_name)
    f.save(tmp_path)

    # Detect file type folder (Images, Videos, Audio, Documents, Others)
    file_type = detect_filetype(str(tmp_path))

    # Generate file UUID
    file_id = str(uuid.uuid4())

    # Final folder structure:
    # uploads/<username>/<FileType>/
    user_type_dir = Path(UPLOADS_DIR) / username / file_type
    user_type_dir.mkdir(parents=True, exist_ok=True)

    # Final filename: uuid.ext
    final_name = f"{file_id}{ext}"
    final_path = user_type_dir / final_name

    # Move file
    tmp_path.replace(final_path)

    # Save metadata in file_index.json
    index = load_json(INDEX_FILE)
    index[file_id] = {
        "path": str(final_path),
        "owner": username,
        "timestamp": int(time.time()),
        "type": file_type,
        "original_name": orig_name,
    }
    save_json(INDEX_FILE, index)

    return jsonify({"file_id": file_id, "file_type": file_type})

# ---------------------------
# DOWNLOAD
# ---------------------------
@app.get("/download/<file_id>")
def download(file_id):
    token = request.headers.get("Authorization")
    username = get_username_from_token(token)

    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    index = load_json(INDEX_FILE)
    if file_id not in index:
        return jsonify({"error": "File not found"}), 404

    entry = index[file_id]
    if entry["owner"] != username:
        return jsonify({"error": "Forbidden"}), 403

    file_path = entry["path"]
    if not os.path.exists(file_path):
        return jsonify({"error": "File missing"}), 500

    filename = os.path.basename(file_path)

    return send_file(file_path, as_attachment=True, download_name=filename)

# ---------------------------
# Health check
# ---------------------------
@app.get("/ping")
def ping():
    return jsonify({"status": "ok"})

# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    print("Backend running on http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000)
