"""
create_user.py

Create a user and store a hashed password in users.json.

Usage:
    python create_user.py
"""

import json
import getpass
from pathlib import Path
from passlib.hash import pbkdf2_sha256

USERS_FILE = "users.json"

def load_users():
    p = Path(USERS_FILE)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_users(users):
    Path(USERS_FILE).write_text(json.dumps(users, indent=4), encoding="utf-8")

def main():
    username = input("Enter username: ").strip()
    if not username:
        print("Invalid username")
        return

    password = getpass.getpass("Enter password: ")
    password2 = getpass.getpass("Confirm password: ")
    if password != password2:
        print("Passwords do not match.")
        return

    users = load_users()
    users[username] = pbkdf2_sha256.hash(password)
    save_users(users)
    print(f"User '{username}' created/updated in {USERS_FILE}")

if __name__ == "__main__":
    main()
