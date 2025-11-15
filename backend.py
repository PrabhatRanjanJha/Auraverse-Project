# backend.py
from flask import Flask, request, jsonify, send_file
import json
import os
import sqlite3
import mimetypes

from backend_core import (
    detect_sql,
    create_sql_db,
    create_doc_db,
    generate_credentials,
    save_user_credentials,
    save_regular_file,
    DB_INDEX,
    USERS_FILE,
)

app = Flask(__name__)
BACKUP_TMP = "temp_upload"
os.makedirs(BACKUP_TMP, exist_ok=True)

# Ensure index files exist (backend_core already does but safe)
for f in (DB_INDEX, USERS_FILE):
    if not os.path.exists(f):
        with open(f, "w", encoding="utf-8") as fh:
            json.dump({}, fh)


def verify_token(token: str):
    # token format: "<username>:<uuid>"
    if not token or ":" not in token:
        return None
    username = token.split(":", 1)[0]
    # check user exists
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as fh:
            users = json.load(fh)
    except Exception:
        return None
    if username in users:
        return username
    return None


def generate_token_for_user(username: str):
    # simple token (not intended to be secure long-term); token returned for front-end login flow
    import uuid
    return f"{username}:{uuid.uuid4().hex}"


@app.post("/login")
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"success": False, "error": "username/password required"}), 400

    # verify credential using passlib stored hash
    from passlib.hash import pbkdf2_sha256
    with open(USERS_FILE, "r", encoding="utf-8") as fh:
        users = json.load(fh)
    if username not in users:
        return jsonify({"success": False, "error": "Invalid login"}), 401
    if not pbkdf2_sha256.verify(password, users[username]):
        return jsonify({"success": False, "error": "Invalid login"}), 401

    token = generate_token_for_user(username)
    return jsonify({"success": True, "token": token})


@app.post("/upload")
def upload():
    token = request.headers.get("Authorization")
    owner = verify_token(token)
    # if upload is done by an anonymous uploader, we still allow uploading regular files but JSON will get new creds.
    # For non-json files, we'll set owner to token username if available, otherwise "anonymous"
    if owner is None:
        uploader = "anonymous"
    else:
        uploader = owner

    # If a file is uploaded
    if "file" in request.files:
        f = request.files["file"]
        filename = f.filename or "uploaded"
        tmp_path = os.path.join(BACKUP_TMP, filename)
        f.save(tmp_path)

        # JSON file handling
        if filename.lower().endswith(".json"):
            try:
                with open(tmp_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                return jsonify({"success": False, "error": "Invalid JSON file"}), 400

            # Normalize to list if dict
            if isinstance(data, dict):
                rows = [data]
            elif isinstance(data, list):
                rows = data
            else:
                return jsonify({"success": False, "error": "Top-level JSON must be object or array"}), 400

            is_sql, reason = detect_sql(rows)
            # create new account (username + password) per Option A
            new_user, new_pass = generate_credentials()
            save_user_credentials(new_user, new_pass)

            if is_sql:
                db_user, db_path = create_sql_db(new_user, rows)
                return jsonify({
                    "success": True,
                    "type": "sql",
                    "username": new_user,
                    "password": new_pass,
                    "reason": reason
                })
            else:
                db_user, db_path = create_doc_db(new_user, data)
                return jsonify({
                    "success": True,
                    "type": "doc",
                    "username": new_user,
                    "password": new_pass,
                    "reason": reason
                })

        # NON-JSON binary files (images/videos/docs)
        with open(tmp_path, "rb") as fh:
            data_bytes = fh.read()
        file_uuid, category, final_path = save_regular_file(tmp_path, uploader_username=uploader, original_name=filename, data_bytes=data_bytes)
        return jsonify({"success": True, "type": category.lower(), "uuid": file_uuid})

    # If text JSON submitted through form field "text_json"
    txt = request.form.get("text_json")
    if txt:
        try:
            obj = json.loads(txt)
        except Exception:
            return jsonify({"success": False, "error": "Invalid JSON text"}), 400

        if isinstance(obj, dict):
            rows = [obj]
        elif isinstance(obj, list):
            rows = obj
        else:
            return jsonify({"success": False, "error": "Top-level JSON must be object or array"}), 400

        is_sql, reason = detect_sql(rows)
        new_user, new_pass = generate_credentials()
        save_user_credentials(new_user, new_pass)
        if is_sql:
            db_user, db_path = create_sql_db(new_user, rows)
            return jsonify({
                "success": True,
                "type": "sql",
                "username": new_user,
                "password": new_pass,
                "reason": reason
            })
        else:
            db_user, db_path = create_doc_db(new_user, obj)
            return jsonify({
                "success": True,
                "type": "doc",
                "username": new_user,
                "password": new_pass,
                "reason": reason
            })

    return jsonify({"success": False, "error": "No input provided"}), 400


@app.get("/download/<code>")
def download(code):
    """
    Downloads either: a regular file (uuid) or a user DB (if code == username)
    For regular files: code is uuid saved in db_index.json
    For JSON-created DBs: code is username (owner) and we look up db_index for that username
    """
    token = request.headers.get("Authorization")
    requester = verify_token(token)  # may be None -> anonymous

    # load index
    try:
        with open(DB_INDEX, "r", encoding="utf-8") as fh:
            index = json.load(fh)
    except Exception:
        index = {}

    # find entry either by uuid key or by username key
    entry = index.get(code)
    if not entry:
        # maybe user wants their own DB by username (json-created DB stored with owner==username)
        # check for username entry
        # we will allow owner to download their own DB if token matches or if admin (no admin concept here)
        # allow download only if token owned by same username
        # treat 'code' as username path (owner name)
        entry = index.get(code)
        if not entry:
            return jsonify({"error": "UUID/username not found"}), 404

    # authorization: for DBs created under a username we only allow owner to download (unless file is public)
    owner = entry.get("owner")
    if owner and requester != owner:
        return jsonify({"error": "Access denied (must be the DB owner to download)"}), 403

    path = entry.get("path")
    if not path or not os.path.exists(path):
        return jsonify({"error": "File not found on server"}), 404

    original_name = entry.get("original_name") or os.path.basename(path)
    mime = entry.get("mime")
    if not mime:
        mime, _ = mimetypes.guess_type(path)
        if not mime:
            mime = "application/octet-stream"

    try:
        return send_file(path, mimetype=mime, as_attachment=True, download_name=original_name)
    except TypeError:
        # older Flask
        return send_file(path, mimetype=mime, as_attachment=True, attachment_filename=original_name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
