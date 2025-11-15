import json
import os
from passlib.hash import pbkdf2_sha256

USERS_FILE = "users.json"


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    confirm = input("Confirm password: ").strip()

    if password != confirm:
        print("Passwords do not match!")
        exit()

    users = load_users()
    users[username] = pbkdf2_sha256.hash(password)

    save_users(users)
    print("User created successfully!")
