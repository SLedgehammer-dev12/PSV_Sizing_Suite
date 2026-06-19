import os
import json
import hashlib
import secrets
import platform

if platform.system() == "Windows":
    _base = os.environ.get("APPDATA", os.path.expanduser("~"))
else:
    _base = os.path.expanduser("~")

APP_DATA_DIR = os.path.join(_base, ".psv_sizing_suite")
os.makedirs(APP_DATA_DIR, exist_ok=True)
AUTH_FILE = os.path.join(APP_DATA_DIR, "auth.json")

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return salt + ':' + key.hex()

def verify_password(password, stored_hash):
    if ':' not in stored_hash:
        return hash_password(password).split(':')[1] == stored_hash
    salt, _ = stored_hash.split(':', 1)
    return hash_password(password, salt) == stored_hash

def init_auth():
    if not os.path.exists(AUTH_FILE):
        default_hash = hash_password("123456")
        data = {
            "user_hash": default_hash,
            "admin_hash": default_hash
        }
        with open(AUTH_FILE, 'w') as f:
            json.dump(data, f)

def check_login(username, password):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)

    if username == "admin":
        return verify_password(password, data.get("admin_hash", ""))
    elif username == "user":
        return verify_password(password, data.get("user_hash", ""))
    return False

def change_password(username, new_password):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)

    data[f"{username}_hash"] = hash_password(new_password)

    with open(AUTH_FILE, 'w') as f:
        json.dump(data, f)
    return True