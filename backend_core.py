# backend_core.py
import os
import json
import uuid
import sqlite3
import secrets
import string
from typing import Tuple, List, Dict, Any
from pathlib import Path
from passlib.hash import pbkdf2_sha256
from datetime import datetime
import mimetypes

# Import classifier to save non-json files into categorized_data
try:
    from classifier import classify_and_save
except Exception:
    classify_and_save = None

ROOT = Path(".").resolve()
DB_INDEX = str(ROOT / "db_index.json")
USERS_FILE = str(ROOT / "users.json")

# Make sure index files exist
for p in (DB_INDEX, USERS_FILE):
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)


def _write_index_entry(uuid_key: str, entry: Dict[str, Any]):
    with open(DB_INDEX, "r+", encoding="utf-8") as fh:
        try:
            idx = json.load(fh)
        except Exception:
            idx = {}
        idx[uuid_key] = entry
        fh.seek(0)
        json.dump(idx, fh, indent=2)
        fh.truncate()


def _load_index() -> Dict[str, Any]:
    with open(DB_INDEX, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except Exception:
            return {}


def generate_credentials() -> Tuple[str, str]:
    # username: user_<short uuid>
    u = f"user_{uuid.uuid4().hex[:10]}"
    # password: 12 char secure
    alphabet = string.ascii_letters + string.digits
    p = "".join(secrets.choice(alphabet) for _ in range(12))
    return u, p


def save_user_credentials(username: str, password_plain: str) -> None:
    # Hash password and store in users.json (create/update)
    with open(USERS_FILE, "r+", encoding="utf-8") as fh:
        try:
            users = json.load(fh)
        except Exception:
            users = {}
        users[username] = pbkdf2_sha256.hash(password_plain)
        fh.seek(0)
        json.dump(users, fh, indent=2)
        fh.truncate()


def verify_user_password(username: str, password_plain: str) -> bool:
    with open(USERS_FILE, "r", encoding="utf-8") as fh:
        try:
            users = json.load(fh)
        except Exception:
            return False
    if username not in users:
        return False
    return pbkdf2_sha256.verify(password_plain, users[username])


# -------------------------
# SQL detection heuristic
# -------------------------
def detect_sql(objects: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Heuristic to decide if JSON objects look relational (SQL) or document-like.
    Returns (is_sql, reason_string)
    Rules:
     - If top-level is list of dicts (or single dict normalized to list) -> candidate SQL.
     - If most values are primitives (str/int/float/bool/null) or lists-of-dicts (subtables), it's SQL.
     - If many deeply nested dicts or heterogeneous structures -> doc.
    """
    if not isinstance(objects, list) or len(objects) == 0:
        return False, "Top-level JSON is not a non-empty list (or normalized single object)."

    def value_type(v):
        if v is None:
            return "primitive"
        if isinstance(v, (int, float, str, bool)):
            return "primitive"
        if isinstance(v, dict):
            return "dict"
        if isinstance(v, list):
            # check list element types
            if all(isinstance(x, dict) for x in v) and len(v) > 0:
                return "list_of_dicts"
            if all(not isinstance(x, (dict, list)) for x in v):
                return "primitive_list"
            return "mixed_list"
        return "other"

    total = len(objects)
    primitive_fields = 0
    list_of_dicts_fields = 0
    dict_fields = 0
    mixed_fields = 0
    samples_checked = min(10, total)

    for obj in objects[:samples_checked]:
        if not isinstance(obj, dict):
            return False, "Not all elements are objects/dicts (so treated as document)."
        for k, v in obj.items():
            t = value_type(v)
            if t == "primitive":
                primitive_fields += 1
            elif t == "primitive_list":
                primitive_fields += 1
            elif t == "list_of_dicts":
                list_of_dicts_fields += 1
            elif t == "dict":
                dict_fields += 1
            else:
                mixed_fields += 1

    # scoring
    score = primitive_fields + (list_of_dicts_fields * 0.8) - (dict_fields * 1.2) - (mixed_fields * 1.0)

    reason = (
        f"primitive_fields={primitive_fields}, list_of_dicts={list_of_dicts_fields}, "
        f"dict_fields={dict_fields}, mixed_fields={mixed_fields}; score={score:.2f}"
    )

    # threshold heuristics: prefer SQL when score positive and not many nested dicts
    if score > 1.0:
        return True, f"Decided SQL-like. {reason}"
    # allow borderline: if no nested dicts but many primitives => SQL
    if dict_fields == 0 and primitive_fields >= 1:
        return True, f"Decided SQL-like (no nested dicts). {reason}"

    return False, f"Decided Document-like. {reason}"


# -------------------------
# Create SQL DB from list-of-dicts
# -------------------------
def create_sql_db(owner_username: str, objects: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Create a sqlite DB for the given owner and objects.
    Returns (username, db_path)
    NOTE: owner_username is the auto-generated username for the database owner.
    """

    # Create user db folder
    user_dir = ROOT / "user_dbs"
    user_dir.mkdir(parents=True, exist_ok=True)

    db_filename = f"{owner_username}.db"
    db_path = str(user_dir / db_filename)

    # Determine columns using first object (best-effort)
    first = objects[0] if objects else {}
    columns = {}
    for k, v in first.items():
        if v is None:
            columns[k] = "TEXT"
        elif isinstance(v, bool):
            columns[k] = "INTEGER"
        elif isinstance(v, int):
            columns[k] = "INTEGER"
        elif isinstance(v, float):
            columns[k] = "REAL"
        elif isinstance(v, (str,)):
            columns[k] = "TEXT"
        elif isinstance(v, list):
            # store lists of primitives or list-of-dict as JSON text (but we'll keep DB main table simple)
            columns[k] = "TEXT"
        else:
            columns[k] = "TEXT"

    # Create sqlite table
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # create main table named 'data'
    try:
        col_defs = ", ".join([f"'{c}' {t}" for c, t in columns.items()])
        if col_defs.strip() == "":
            col_defs = "rowid INTEGER"
        cur.execute(f"CREATE TABLE IF NOT EXISTS data ({col_defs})")
    except Exception:
        # fallback to generic JSON column
        cur.execute("CREATE TABLE IF NOT EXISTS data (payload TEXT)")
        columns = {"payload": "TEXT"}
    # Insert rows
    insert_cols = list(columns.keys())
    placeholders = ", ".join(["?"] * len(insert_cols))
    col_list_sql = ", ".join([f"'{c}'" for c in insert_cols])

    for obj in objects:
        # prepare row values in same order
        vals = []
        for c in insert_cols:
            v = obj.get(c, None)
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v, ensure_ascii=False))
            else:
                vals.append(v)
        try:
            cur.execute(f"INSERT INTO data ({col_list_sql}) VALUES ({placeholders})", vals)
        except Exception:
            # last resort: store the entire object as payload
            cur.execute("INSERT INTO data (payload) VALUES (?)", (json.dumps(obj, ensure_ascii=False),))
    conn.commit()
    conn.close()

    # record in index
    entry = {
        "type": "sql",
        "owner": owner_username,
        "path": db_path,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    _write_index_entry(owner_username, entry)
    return owner_username, db_path


# -------------------------
# Create document DB (store JSON snapshot)
# -------------------------
def create_doc_db(owner_username: str, obj: Any) -> Tuple[str, str]:
    user_dir = ROOT / "user_docs"
    user_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{owner_username}.json"
    path = str(user_dir / file_name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)

    entry = {
        "type": "doc",
        "owner": owner_username,
        "path": path,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    _write_index_entry(owner_username, entry)
    return owner_username, path


# -------------------------
# Save regular (non-json) file
# -------------------------
def save_regular_file(tmp_path: str, uploader_username: str, original_name: str, data_bytes: bytes) -> Tuple[str, str, str]:
    """
    Save a binary file into categorized_data using classifier.classify_and_save (if available),
    otherwise fallback to simple categorization by mimetype/extension.
    Returns (file_uuid, category, final_path)
    """
    # generate uuid for file
    file_uuid = uuid.uuid4().hex
    folder = "Others"
    ext = Path(original_name).suffix or ""
    # try classifier
    if classify_and_save is not None:
        class_file_obj = None
        # we need a small wrapper object with .filename and .stream and .save semantics
        class FileLike:
            def __init__(self, filename, data):
                self.filename = filename
                self._data = data
                from io import BytesIO
                self.stream = BytesIO(data)
            def save(self, path):
                with open(path, "wb") as fh:
                    fh.write(self._data)
            def read(self, n=-1):
                return self._data

        class_file_obj = FileLike(original_name, data_bytes)
        try:
            final_path = classify_and_save(class_file_obj, base_dir="categorized_data", file_id=file_uuid)
            category = Path(final_path).parent.name
            entry = {
                "type": category.lower(),
                "owner": uploader_username,
                "path": str(final_path),
                "original_name": original_name,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
            _write_index_entry(file_uuid, entry)
            return file_uuid, category, str(final_path)
        except Exception:
            pass

    # fallback: mimic classifier by extension/mime
    mime, _ = mimetypes.guess_type(original_name)
    if mime:
        main = mime.split("/")[0]
        if main == "image":
            folder = "Images"
        elif main == "video":
            folder = "Videos"
        elif main == "audio":
            folder = "Audio"
        else:
            folder = "Documents"
    else:
        folder = "Others"

    dest_dir = ROOT / "categorized_data" / folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"{file_uuid}{ext}"
    final_path = str(dest_dir / final_name)
    with open(final_path, "wb") as fh:
        fh.write(data_bytes)

    entry = {
        "type": folder.lower(),
        "owner": uploader_username,
        "path": final_path,
        "original_name": original_name,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    _write_index_entry(file_uuid, entry)
    return file_uuid, folder, final_path
