import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def sandbox_auth_file(tmp_path, monkeypatch):
    """Redirect the credential store to a per-test temp file.

    Defense in depth: even if a test forgets to isolate itself, it can never
    read or delete the user's real auth.json.
    """
    import desktop.auth as auth
    target = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "AUTH_FILE", str(target), raising=False)
    yield str(target)
