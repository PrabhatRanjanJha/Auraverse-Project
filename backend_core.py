# backend_core.py

import os
import uuid
import json
import sqlite3
import mimetypes

DB_INDEX = "db_index.json"

# Ensure DB index exists
if not os.path.exists(DB_INDEX):
    with open(DB_INDEX, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4)


# ----------------------------------------------------
# SQL DETECTION LOGIC
# ----------------------------------------------------
def detect_sql(rows):
    """
    Decide SQL vs Document DB.
    Rule: if all rows share identical keys -> SQL.
    """
    if not isinstance(rows, list) or len(rows) == 0:
        return False, "Empty or invalid JSON"

    first_keys = set(rows[0].keys())
    for r in rows[1:]:
        if set(r.keys()) != first_keys:
            return False, "Rows don't have identical columns → Document DB"

    return True, "All rows share consistent columns → SQL database"


# ----------------------------------------------------
# CREATE SQL DATABASE
# ----------------------------------------------------
def create_sql_db(username, rows):
    os.makedirs("databases", exist_ok=True)

    db_uuid = uuid.uuid4().hex
    db_path = f"databases/{db_uuid}.db"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create table
    cols = rows[0].keys()
    col_defs = ", ".join([f"{c} TEXT" for c in cols])
    cur.execute(f"CREATE TABLE data ({col_defs})")

    # Insert rows
    for r in rows:
        vals = [str(r[c]) for c in cols]
        placeholders = ",".join(["?"] * len(vals))
        cur.execute(f"INSERT INTO data VALUES ({placeholders})", vals)

    conn.commit()
    conn.close()

    # Update index
    with open(DB_INDEX, "r", encoding="utf-8") as f:
        index = json.load(f)

    index[db_uuid] = {
        "path": db_path,
        "type": "sql",
        "owner": username,
        "original_name": f"{db_uuid}.db",
        "mime": "application/octet-stream"
    }

    with open(DB_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=4)

    return db_uuid, db_path


# ----------------------------------------------------
# CREATE DOCUMENT DATABASE
# ----------------------------------------------------
def create_doc_db(username, obj):
    os.makedirs("databases", exist_ok=True)

    db_uuid = uuid.uuid4().hex
    db_path = f"databases/{db_uuid}.json"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4)

    # Update index
    with open(DB_INDEX, "r") as f:
        index = json.load(f)

    index[db_uuid] = {
        "path": db_path,
        "type": "doc",
        "owner": username,
        "original_name": f"{db_uuid}.json",
        "mime": "application/json"
    }

    with open(DB_INDEX, "w") as f:
        json.dump(index, f, indent=4)

    return db_uuid, db_path


# ----------------------------------------------------
# SAVE REGULAR (NON-JSON) FILES — FIXED 100%
# ----------------------------------------------------
def save_regular_file(temp_path, username, original_name, data_bytes):
    os.makedirs("categorized_data", exist_ok=True)

    mime, _ = mimetypes.guess_type(original_name)
    if not mime:
        mime = "application/octet-stream"

    # Categorize
    if mime.startswith("image/"):
        category = "images"
    elif mime.startswith("video/") or mime.startswith("audio/"):
        category = "videos"
    elif mime == "application/pdf":
        category = "pdf"
    else:
        category = "other"

    final_folder = f"categorized_data/{category}"
    os.makedirs(final_folder, exist_ok=True)

    file_uuid = uuid.uuid4().hex
    ext = os.path.splitext(original_name)[1]
    final_path = f"{final_folder}/{file_uuid}{ext}"

    # WRITE IN PURE BINARY — FIXES CORRUPTION
    with open(final_path, "wb") as out:
        out.write(data_bytes)

    # Update index
    with open(DB_INDEX, "r") as f:
        index = json.load(f)

    index[file_uuid] = {
        "path": final_path,
        "owner": username,
        "mime": mime,
        "original_name": original_name,
        "type": category
    }

    with open(DB_INDEX, "w") as f:
        json.dump(index, f, indent=4)

    os.remove(temp_path)

    return file_uuid, category, final_path
