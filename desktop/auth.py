import os
import json
import secrets
import sys
import hashlib
import time

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUTH_FILE = os.path.join(get_base_path(), 'auth.json')
DEFAULT_PASSWORD = "123456"

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300

def hash_password(password):
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    else:
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 200000)
        return f"$pbkdf2${salt}${dk.hex()}"

def verify_password(password, stored_hash):
    if stored_hash.startswith("$pbkdf2$"):
        _, salt, h = stored_hash.split("$", 3)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 200000)
        return dk.hex() == h
    elif stored_hash.startswith("$sha256$"):
        _, salt, h = stored_hash.split("$", 3)
        recomputed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
        return recomputed == h
    elif HAS_BCRYPT:
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    else:
        return False

def is_default_password(username):
    return verify_password(DEFAULT_PASSWORD, get_hash(username))

def get_hash(username):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)
    return data.get(f"{username}_hash", "")

def must_change_password(username):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)
    return data.get(f"{username}_must_change", False)

def set_password_changed(username):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)
    data[f"{username}_must_change"] = False
    with open(AUTH_FILE, 'w') as f:
        json.dump(data, f)

def init_auth():
    if not os.path.exists(AUTH_FILE):
        data = {
            "user_hash": hash_password(DEFAULT_PASSWORD),
            "admin_hash": hash_password(DEFAULT_PASSWORD),
            "user_must_change": True,
            "admin_must_change": True,
            "version": 2
        }
        with open(AUTH_FILE, 'w') as f:
            json.dump(data, f)
    else:
        with open(AUTH_FILE, 'r') as f:
            data = json.load(f)
        changed = False
        if "version" not in data or data["version"] < 2:
            data["version"] = 2
            if "user_hash" in data and not data["user_hash"].startswith("$"):
                data["user_hash"] = hash_password(DEFAULT_PASSWORD)
                data["user_must_change"] = True
            if "admin_hash" in data and not data["admin_hash"].startswith("$"):
                data["admin_hash"] = hash_password(DEFAULT_PASSWORD)
                data["admin_must_change"] = True
            changed = True
        if "user_must_change" not in data:
            data["user_must_change"] = is_default_password("user")
            changed = True
        if "admin_must_change" not in data:
            data["admin_must_change"] = is_default_password("admin")
            changed = True
        if changed:
            with open(AUTH_FILE, 'w') as f:
                json.dump(data, f)

def check_login(username, password):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)

    lockout_key = f"{username}_lockout_until"
    if lockout_key in data:
        lockout_until = data[lockout_key]
        if time.time() < lockout_until:
            remaining = int(lockout_until - time.time())
            return False

    fail_key = f"{username}_failed_attempts"
    failed = data.get(fail_key, 0)

    pw_hash = data.get(f"{username}_hash")
    if not pw_hash:
        return False

    if verify_password(password, pw_hash):
        if fail_key in data:
            data.pop(fail_key, None)
            data.pop(lockout_key, None)
            with open(AUTH_FILE, 'w') as fw:
                json.dump(data, fw)
        return True
    else:
        failed += 1
        data[fail_key] = failed
        if failed >= MAX_FAILED_ATTEMPTS:
            data[lockout_key] = time.time() + LOCKOUT_DURATION_SECONDS
        with open(AUTH_FILE, 'w') as fw:
            json.dump(data, fw)
        return False

def change_password(username, new_password):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)

    data[f"{username}_hash"] = hash_password(new_password)
    data[f"{username}_must_change"] = False
    data.pop(f"{username}_failed_attempts", None)
    data.pop(f"{username}_lockout_until", None)

    with open(AUTH_FILE, 'w') as f:
        json.dump(data, f)
    return True

def get_lockout_remaining(username):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)
    lockout_key = f"{username}_lockout_until"
    if lockout_key in data:
        remaining = data[lockout_key] - time.time()
        if remaining > 0:
            return int(remaining)
    return 0
