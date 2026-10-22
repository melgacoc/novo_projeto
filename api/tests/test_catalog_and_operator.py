
from io import BytesIO

from PIL import Image

from app.models import Category, Operator, OperatorMember, User
from app.services.schedule_service import today_local
from tests.conftest import as_role

TOUR_BODY = {
    "category_id": None,
    "duration_minutes": 120,
    "public_area_label": "Copacabana",
    "meeting_point_address": "Av. Atlântica, 1",
    "meeting_lat": -22.9711,
    "meeting_lng": -43.1863,
    "cancellation_policy": "flexible",
    "translations": [
        {"locale": loc, "title": f"Passeio de barco {loc}", "summary": "Resumo", "description": "Descrição"}
        for loc in ("pt", "es", "en")
    ],
    "price_categories": [
        {"code": "adult", "label_pt": "Adulto", "prices": [{"price_cents": 9900, "valid_from": "2020-01-01"}]}
    ],
}


def _png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (40, 30), (10, 120, 200)).save(out, format="PNG")
    return out.getvalue()


def _setup_operator(db) -> Operator:
    dev = db.query(User).filter_by(email="operadora.dev@tur.local").one()
    op = Operator(public_name="Minha Op", trade_name="Minha Op", status="active")
    db.add(op)
    db.flush()
    db.add(OperatorMember(operator_id=op.id, user_id=dev.id))
    db.commit()
    return op


def test_operator_creates_submits_and_admin_publishes(client, db):
    op = _setup_operator(db)
    h = as_role("operator", op.id)
    body = dict(TOUR_BODY, category_id=db.query(Category).first().id)
    tour = client.post("/api/v1/operator/tours", headers=h, json=body).json()
    assert tour["status"] == "draft" and tour["slug"] == "passeio-de-barco-pt"
    assert tour["from_price_cents"] == 9900 and tour["public_lat"] == -22.97

    r = client.post(f"/api/v1/operator/tours/{tour['id']}/submit", headers=h)
    assert r.status_code == 400
    assert "missing_photo" in r.json()["error"]["details"]["problems"]

    up = client.post(f"/api/v1/operator/tours/{tour['id']}/photos", headers=h,
                     files={"file": ("x.png", _png(), "image/png")})
    assert up.status_code == 201, up.text
    bad = client.post(f"/api/v1/operator/tours/{tour['id']}/photos", headers=h,
                      files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 400

    sched = client.post(f"/api/v1/operator/tours/{tour['id']}/schedules", headers=h, json={
        "weekdays": [0, 1, 2, 3, 4, 5, 6], "start_time": "09:00", "capacity": 10,
        "valid_from": today_local().isoformat()})
    assert sched.status_code == 201
    deps = client.get("/api/v1/operator/departures", headers=h, params={"tour_id": tour["id"]}).json()
    assert len(deps) >= 14

    assert client.post(f"/api/v1/operator/tours/{tour['id']}/submit", headers=h).json()["status"] == "pending_review"
    assert client.get(f"/api/v1/tours/{tour['slug']}").status_code == 404  # ainda não publicado
    pub = client.post(f"/api/v1/admin/tours/{tour['id']}/approve", headers=as_role("admin"), json={})
    assert pub.json()["status"] == "published"
    assert client.get(f"/api/v1/tours/{tour['slug']}?locale=en").json()["title"] == "Passeio de barco en"

    found = client.get("/api/v1/tours", params={"q": "barco", "available": True}).json()
    assert found["total"] == 1


def test_contact_flags(client, db):
    op = _setup_operator(db)
    body = dict(TOUR_BODY)
    body["translations"] = [dict(TOUR_BODY["translations"][0], description="Fale no WhatsApp (21) 99999-8888 ou @meuinsta")]
    t = client.post("/api/v1/operator/tours", headers=as_role("operator", op.id), json=body).json()
    detail = client.get(f"/api/v1/operator/tours/{t['id']}", headers=as_role("operator", op.id)).json()
    kinds = {f["kind"] for f in detail["contact_flags"]}
    assert {"phone", "handle", "whatsapp"} <= kinds


def test_seasonal_price_validation(client, db):
    op = _setup_operator(db)
    body = dict(TOUR_BODY)
    body["price_categories"] = [{"code": "adult", "prices": [
        {"price_cents": 100, "valid_from": "2026-01-01", "valid_to": "2026-06-30"},
        {"price_cents": 200, "valid_from": "2026-06-01"}]}]
    r = client.post("/api/v1/operator/tours", headers=as_role("operator", op.id), json=body)
    assert r.status_code == 422


def test_departure_capacity_cannot_go_below_booked(client, make_tour):
    op, _, dep = make_tour(capacity=3)
    client.post("/api/v1/bookings", headers=as_role("tourist"), json={
        "departure_id": dep.id, "quantities": {"adult": 2}, "contact_name": "Ana", "contact_phone": "21988887777"})
    r = client.patch(f"/api/v1/operator/departures/{dep.id}", headers=as_role("admin", op.id), json={"capacity": 1})
    assert r.status_code == 409


def test_search_geo_and_price(client, make_tour):
    make_tour(price=50_00)
    make_tour(price=500_00)
    r = client.get("/api/v1/tours", params={"lat": -22.97, "lng": -43.18, "radius_km": 5, "sort": "price"}).json()
    assert [i["from_price_cents"] for i in r["items"]] == [50_00, 500_00]
    far = client.get("/api/v1/tours", params={"lat": -23.5, "lng": -46.6, "radius_km": 5}).json()
    assert far["total"] == 0
    cheap = client.get("/api/v1/tours", params={"price_max": 100_00}).json()
    assert cheap["total"] == 1


def test_public_departures_availability_label(client, make_tour):
    _, tour, dep = make_tour(capacity=10)
    d = client.get(f"/api/v1/tours/{tour.slug}/departures").json()
    assert d[0]["availability"] == "available" and "capacity" not in d[0]


def test_settings_and_audit(client):
    r = client.patch("/api/v1/admin/settings", headers=as_role("admin"), json={"default_commission_rate": "0.12"})
    assert r.json()["default_commission_rate"] == "0.12"
    logs = client.get("/api/v1/admin/audit-logs", headers=as_role("admin"), params={"entity": "settings"}).json()
    assert logs["total"] == 1


