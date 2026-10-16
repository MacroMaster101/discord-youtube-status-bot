"""Dashboard login, session tokens and password rules, through the real Flask routes."""
import json
import secrets

import pytest

from config import Config
from core.passwords import hash_password, verify_password
from web import auth
from web.app import create_app


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Never read or write the real data/config.json or .env."""
    monkeypatch.setattr(Config, "PERSISTENT_CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(Config, "ADMIN_PASSWORD_HASH", "")
    monkeypatch.setattr(Config, "update_env", classmethod(lambda cls, k, v: setattr(cls, k, v)))
    auth.revoke_all_sessions()
    return tmp_path / "config.json"


@pytest.fixture
def password(monkeypatch):
    value = secrets.token_urlsafe(12)
    monkeypatch.setattr(Config, "ADMIN_PASSWORD", value)
    return value


@pytest.fixture
def client():
    return create_app(bot=None).test_client()


def _login(client, pw):
    return client.post("/api/login", json={"password": pw})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("value", ["", "admin123", "change_me", "short"])
def test_strength_issue_rejects_weak_values(value):
    assert auth.strength_issue(value)


def test_strength_issue_accepts_strong_value():
    assert auth.strength_issue(secrets.token_urlsafe(12)) is None


def test_hash_roundtrip_and_salting():
    value = secrets.token_urlsafe(12)
    first, second = hash_password(value), hash_password(value)
    assert first != second and value not in first  # salted, never contains the password
    assert verify_password(value, first) and verify_password(value, second)
    assert not verify_password(value + "x", first)
    assert not verify_password(value, "not-a-hash")


def test_login_returns_random_token_not_the_password(client, password):
    r = _login(client, password)
    assert r.status_code == 200
    token = r.get_json()["token"]
    assert token and token != password
    assert _login(client, password).get_json()["token"] != token  # new token per login


def test_wrong_password_is_rejected(client, password):
    assert _login(client, password + "x").status_code == 401


def test_password_is_not_accepted_as_bearer_token(client, password):
    assert client.get("/api/logs", headers=_auth(password)).status_code == 401


def test_session_token_grants_access_until_logout(client, password):
    token = _login(client, password).get_json()["token"]
    assert client.get("/api/logs", headers=_auth(token)).status_code == 200
    assert client.post("/api/logout", headers=_auth(token)).status_code == 200
    assert client.get("/api/logs", headers=_auth(token)).status_code == 401


def test_expired_session_is_rejected(client, password, monkeypatch):
    token = _login(client, password).get_json()["token"]
    real_time = auth.time.time
    monkeypatch.setattr(auth.time, "time", lambda: real_time() + auth.SESSION_TTL_SECONDS + 1)
    assert client.get("/api/logs", headers=_auth(token)).status_code == 401


@pytest.mark.parametrize("weak", ["", "admin123", "change_me"])
def test_login_disabled_while_password_is_weak(client, monkeypatch, weak):
    monkeypatch.setattr(Config, "ADMIN_PASSWORD", weak)
    r = _login(client, weak)
    assert r.status_code == 503
    assert "disabled" in r.get_json()["message"]


def test_changing_password_logs_out_other_sessions(client, password):
    old = _login(client, password).get_json()["token"]
    other = _login(client, password).get_json()["token"]
    new_password = secrets.token_urlsafe(12)

    r = client.post("/api/config", headers=_auth(old), json={"ADMIN_PASSWORD": new_password})
    assert r.status_code == 200
    fresh = r.get_json()["token"]

    assert client.get("/api/logs", headers=_auth(other)).status_code == 401
    assert client.get("/api/logs", headers=_auth(old)).status_code == 401
    assert client.get("/api/logs", headers=_auth(fresh)).status_code == 200
    assert _login(client, new_password).status_code == 200


def test_weak_new_password_is_refused(client, password):
    token = _login(client, password).get_json()["token"]
    r = client.post("/api/config", headers=_auth(token), json={"ADMIN_PASSWORD": "admin123"})
    assert r.status_code == 400
    assert Config.ADMIN_PASSWORD == password


def test_dashboard_password_change_stores_only_a_hash(client, password, isolated_config):
    token = _login(client, password).get_json()["token"]
    new_password = secrets.token_urlsafe(12)
    client.post("/api/config", headers=_auth(token), json={"ADMIN_PASSWORD": new_password})

    saved = isolated_config.read_text(encoding="utf-8")
    assert new_password not in saved
    assert json.loads(saved)["ADMIN_PASSWORD_HASH"].startswith("scrypt$")
    assert _login(client, password).status_code == 401  # old .env password no longer works


def test_legacy_plaintext_password_is_migrated_to_hash(password, isolated_config, monkeypatch):
    legacy = secrets.token_urlsafe(12)
    isolated_config.write_text(json.dumps({"ADMIN_PASSWORD": legacy, "PREFIX": "!"}), encoding="utf-8")
    monkeypatch.setattr(Config, "PREFIX", "$")

    Config.load_persistent()

    saved = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert "ADMIN_PASSWORD" not in saved and saved["PREFIX"] == "!"
    assert auth.check_password(legacy)
