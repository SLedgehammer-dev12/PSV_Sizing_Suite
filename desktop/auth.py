import os
import json
import secrets
import sys
import hashlib
import logging
import time

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

logger = logging.getLogger(__name__)

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PSV Sizing Suite')
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# PSV_AUTH_FILE lets deployments and tests redirect the credential store
# without ever touching the user's real auth.json.
AUTH_FILE = os.environ.get('PSV_AUTH_FILE') or os.path.join(get_base_path(), 'auth.json')
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
    if not isinstance(stored_hash, str) or not stored_hash:
        return False
    if stored_hash.startswith("$pbkdf2$"):
        _, _, salt, h = stored_hash.split("$", 3)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 200000)
        return secrets.compare_digest(dk.hex(), h)
    elif stored_hash.startswith("$sha256$"):
        _, _, salt, h = stored_hash.split("$", 3)
        recomputed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
        return secrets.compare_digest(recomputed, h)
    elif HAS_BCRYPT:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        except ValueError:
            return False
    else:
        return False

def _is_default_hash(stored_hash):
    """True when a stored hash is missing or still matches the default password."""
    if not isinstance(stored_hash, str) or not stored_hash:
        return True
    return verify_password(DEFAULT_PASSWORD, stored_hash)

def _default_auth_data():
    return {
        "user_hash": hash_password(DEFAULT_PASSWORD),
        "admin_hash": hash_password(DEFAULT_PASSWORD),
        "user_must_change": True,
        "admin_must_change": True,
        "version": 2
    }

def _write_auth_data(data):
    with open(AUTH_FILE, 'w') as f:
        json.dump(data, f)

def _read_auth_data():
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("auth file does not contain a JSON object")
    return data

def _quarantine_corrupt_file():
    try:
        backup = f"{AUTH_FILE}.corrupt-{int(time.time())}"
        os.replace(AUTH_FILE, backup)
        logger.warning("Corrupt auth file moved to %s; defaults restored.", backup)
    except OSError as exc:
        logger.error("Could not quarantine corrupt auth file: %s", exc)

def is_default_password(username):
    return verify_password(DEFAULT_PASSWORD, get_hash(username))

def get_hash(username):
    init_auth()
    data = _read_auth_data()
    return data.get(f"{username}_hash", "")

def must_change_password(username):
    init_auth()
    data = _read_auth_data()
    return data.get(f"{username}_must_change", False)

def set_password_changed(username):
    init_auth()
    data = _read_auth_data()
    data[f"{username}_must_change"] = False
    _write_auth_data(data)

def init_auth():
    auth_dir = os.path.dirname(AUTH_FILE) or "."
    os.makedirs(auth_dir, exist_ok=True)

    if not os.path.exists(AUTH_FILE):
        _write_auth_data(_default_auth_data())
        return

    try:
        data = _read_auth_data()
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        logger.warning("Could not read auth file (%s). Restoring defaults.", exc)
        _quarantine_corrupt_file()
        _write_auth_data(_default_auth_data())
        return

    changed = False
    if "version" not in data or data["version"] < 2:
        data["version"] = 2
        if "user_hash" in data and not str(data["user_hash"]).startswith("$"):
            data["user_hash"] = hash_password(DEFAULT_PASSWORD)
            data["user_must_change"] = True
        if "admin_hash" in data and not str(data["admin_hash"]).startswith("$"):
            data["admin_hash"] = hash_password(DEFAULT_PASSWORD)
            data["admin_must_change"] = True
        changed = True
    if "user_must_change" not in data:
        data["user_must_change"] = _is_default_hash(data.get("user_hash"))
        changed = True
    if "admin_must_change" not in data:
        data["admin_must_change"] = _is_default_hash(data.get("admin_hash"))
        changed = True
    if changed:
        _write_auth_data(data)

def check_login(username, password):
    init_auth()
    data = _read_auth_data()

    lockout_key = f"{username}_lockout_until"
    if lockout_key in data:
        lockout_until = data[lockout_key]
        if time.time() < lockout_until:
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
            _write_auth_data(data)
        return True
    else:
        failed += 1
        data[fail_key] = failed
        if failed >= MAX_FAILED_ATTEMPTS:
            data[lockout_key] = time.time() + LOCKOUT_DURATION_SECONDS
        _write_auth_data(data)
        return False

def change_password(username, new_password):
    init_auth()
    data = _read_auth_data()

    data[f"{username}_hash"] = hash_password(new_password)
    data[f"{username}_must_change"] = False
    data.pop(f"{username}_failed_attempts", None)
    data.pop(f"{username}_lockout_until", None)

    _write_auth_data(data)
    return True

def get_lockout_remaining(username):
    init_auth()
    data = _read_auth_data()
    lockout_key = f"{username}_lockout_until"
    if lockout_key in data:
        remaining = data[lockout_key] - time.time()
        if remaining > 0:
            return int(remaining)
    return 0
