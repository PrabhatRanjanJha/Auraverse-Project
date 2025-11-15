"""
create_user.py
Creates users with hashed passwords into users.json
USING pbkdf2_sha256 (safe & windows-friendly)
"""

import json
import getpass
from pathlib import Path
from passlib.hash import pbkdf2_sha256

USERS_FILE = "users.json"

def load_users():
    if not Path(USERS_FILE).exists():
        return {}
    return json.loads(Path(USERS_FILE).read_text())

def save_users(data):
    Path(USERS_FILE).write_text(json.dumps(data, indent=4))

if __name__ == "__main__":
    username = input("Enter username: ").strip()
    password = getpass.getpass("Enter password: ")
    password2 = getpass.getpass("Confirm password: ")

    if password != password2:
        print("Passwords do not match.")
        exit()

    users = load_users()
    users[username] = pbkdf2_sha256.hash(password)   # << CHANGED HERE
    save_users(users)

    print("User created:", username)
