"""
backend.py - Flask backend
Run:
    python backend.py

Handles:
- Login (pbkdf2_sha256 password hashing)
- Session tokens
- File uploads
- UUID assignment
- MIME classification using classifier.py
- Saves files ONLY on this machine
- Per-user file access
- File downloads via UUID
"""

import os
import json
import uuid
import time
from pathlib import Path
from flask import Flask, request, send_file, jsonify
from passlib.hash import pbkdf2_sha256
from classifier import classify_and_organize

app = Flask(__name__)

USERS_FILE = "users.json"
INDEX_FILE = "file_index.json"
SESSION_FILE = "sessions.json"
BASE_DIR = "categorized_data"

# -------------------------
# JSON helpers
# -------------------------
def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        return json.loads(Path(path).read_text())
    except:
        return {}

def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=4))


# -------------------------
# Authentication
# -------------------------
def authenticate(username, password):
    users = load_json(USERS_FILE)
    if username not in users:
        return False
    return pbkdf2_sha256.verify(password, users[username])


def create_session(username):
    sessions = load_json(SESSION_FILE)
    token = str(uuid.uuid4())
    sessions[token] = {
        "username": username,
        "created_at": int(time.time())
    }
    save_json(SESSION_FILE, sessions)
    return token


def get_user_from_token(token):
    if not token:
        return None
    sessions = load_json(SESSION_FILE)
    return sessions.get(token, {}).get("username")


# -------------------------
# ROUTES
# -------------------------

@app.post("/login")
def login():
    """
    Logs a user in.
    Returns a session token if successful.
    """
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if authenticate(username, password):
        token = create_session(username)
        return jsonify({"success": True, "token": token})

    return jsonify({"success": False, "msg": "Invalid credentials"}), 401


@app.post("/upload")
def upload():
    """
    Upload endpoint.
    Saves file to categorized_data based on MIME.
    Returns a generated UUID.
    """
    token = request.headers.get("Authorization")
    username = get_user_from_token(token)

    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    # Temporary save
    tmp_path = f"temp_{uuid.uuid4()}"
    file.save(tmp_path)

    # Create unique file ID
    file_id = str(uuid.uuid4())

    # Categorize + Move
    file_type, new_path = classify_and_organize(tmp_path, BASE_DIR, uid=file_id)

    # Save metadata
    index = load_json(INDEX_FILE)
    index[file_id] = {
        "path": new_path,
        "type": file_type,
        "owner": username,
        "timestamp": time.time()
    }
    save_json(INDEX_FILE, index)

    return jsonify({"file_id": file_id, "file_type": file_type})


@app.get("/download/<file_id>")
def download(file_id):
    """
    Download endpoint.
    Only the owner of a file can download it.
    """
    token = request.headers.get("Authorization")
    username = get_user_from_token(token)

    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    index = load_json(INDEX_FILE)

    if file_id not in index:
        return jsonify({"error": "File not found"}), 404

    entry = index[file_id]

    if entry["owner"] != username:
        return jsonify({"error": "Forbidden"}), 403

    return send_file(entry["path"], as_attachment=True)


# -------------------------
# START SERVER
# -------------------------
if __name__ == "__main__":
    # Ensures folders exist
    Path(BASE_DIR).mkdir(exist_ok=True)
    print("Backend running at http://localhost:8000")
    app.run(host="0.0.0.0", port=8000)
