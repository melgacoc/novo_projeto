import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.models import Operator, OperatorMember, User
from app.services import email_service
from tests.conftest import as_role


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_dev_mode_roles(client):
    assert client.get("/api/v1/me").status_code == 401
    me = client.get("/api/v1/me", headers=as_role("tourist")).json()
    assert me["role"] == "tourist" and me["is_dev_user"]
    assert client.get("/api/v1/admin/metrics", headers=as_role("tourist")).status_code == 403
    assert client.get("/api/v1/admin/metrics", headers=as_role("operator")).status_code == 403
    assert client.get("/api/v1/admin/metrics", headers=as_role("admin")).status_code == 200
    assert client.get("/api/v1/operator/tours", headers=as_role("tourist")).status_code == 403


def test_operator_scope(client, db):
    dev_op = db.query(User).filter_by(email="operadora.dev@tur.local").one()
    mine = Operator(public_name="Minha", trade_name="Minha", status="active")
    other = Operator(public_name="Outra", trade_name="Outra", status="active")
    db.add_all([mine, other])
    db.flush()
    db.add(OperatorMember(operator_id=mine.id, user_id=dev_op.id))
    db.commit()
    assert client.get("/api/v1/operator/profile", headers=as_role("operator", mine.id)).json()["id"] == mine.id
    r = client.get("/api/v1/operator/profile", headers=as_role("operator", other.id))
    assert r.status_code == 403
    # admin pode atuar em qualquer operadora
    assert client.get("/api/v1/operator/profile", headers=as_role("admin", other.id)).status_code == 200


def test_auth_endpoints_disabled(client):
    r = client.post("/api/v1/auth/email/request-code", json={"email": "a@b.com"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "auth_disabled"


def test_production_guards():
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_enabled=False, secret_key="x" * 40, database_url="postgresql://x",
                 payment_gateway="other")
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_enabled=True, secret_key="x" * 40, database_url="postgresql://x",
                 payment_gateway="fake")


def test_email_login_refresh_and_reuse(client, monkeypatch):
    settings.auth_enabled = True
    sent = {}

    def fake_enqueue(to, subject, html, attach_voucher_booking_id=None):
        sent["subject"] = subject

    monkeypatch.setattr(email_service, "enqueue_email", fake_enqueue)
    # dev headers são ignorados com login ligado
    assert client.get("/api/v1/me", headers=as_role("admin")).status_code == 401

    assert client.post("/api/v1/auth/email/request-code", json={"email": "Ana@Ex.com", "locale": "es"}).status_code == 200
    code = sent["subject"].split(": ")[1]
    assert client.post("/api/v1/auth/email/verify", json={"email": "ana@ex.com", "code": "000000"}).status_code == 400
    r = client.post("/api/v1/auth/email/verify", json={"email": "ana@ex.com", "code": code})
    assert r.status_code == 200
    access = r.json()["access_token"]
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {access}"}).json()
    assert me["email"] == "ana@ex.com" and me["role"] == "tourist"

    old_refresh = client.cookies.get("tur_refresh")
    csrf = client.cookies.get("tur_csrf")
    assert client.post("/api/v1/auth/refresh").status_code == 403  # sem CSRF
    r = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200 and r.json()["access_token"]

    # reutilizar o refresh antigo revoga a família inteira
    client.cookies.set("tur_refresh", old_refresh, path="/api/v1/auth")
    csrf = client.cookies.get("tur_csrf")
    assert client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf}).status_code == 401
