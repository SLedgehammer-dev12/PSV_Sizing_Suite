import os
import json
import hashlib

import sys

def get_base_path():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # If the application is run from a Python interpreter
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUTH_FILE = os.path.join(get_base_path(), 'auth.json')

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

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
        
    pw_hash = hash_password(password)
    
    if username == "admin":
        return pw_hash == data.get("admin_hash")
    elif username == "user":
        return pw_hash == data.get("user_hash")
    return False

def change_password(username, new_password):
    init_auth()
    with open(AUTH_FILE, 'r') as f:
        data = json.load(f)
        
    data[f"{username}_hash"] = hash_password(new_password)
    
    with open(AUTH_FILE, 'w') as f:
        json.dump(data, f)
    return True
