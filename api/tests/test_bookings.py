from datetime import timedelta

from sqlalchemy import update

from app.core.security import now_utc
from app.models import Booking, Departure, Operator, Refund
from app.services import booking_service, payout_service
from tests.conftest import as_role

H = as_role("tourist")


def _book(client, dep_id, qty=1, phone="+5521988887777"):
    return client.post("/api/v1/bookings", headers=H, json={
        "departure_id": dep_id, "quantities": {"adult": qty}, "contact_name": "Ana", "contact_phone": phone,
        "locale": "pt"})


def _pay(client, code, method="pix"):
    r = client.post(f"/api/v1/bookings/{code}/payments", headers=H, json={"method": method})
    assert r.status_code == 200, r.text
    charge = r.json()["payment"]["charge_id"]
    return client.post(f"/api/v1/dev/payments/{charge}/simulate", headers=H)


def test_full_flow_and_private_data(client, make_tour):
    op, tour, dep = make_tour(price=150_00)
    r = _book(client, dep.id, qty=2)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "held" and b["total_cents"] == 300_00 and "private" not in b
    r = _pay(client, b["code"])
    assert r.json()["status"] == "confirmed"
    assert r.json()["private"]["operator_phone"] == "+5521911112222"
    v = client.get(f"/api/v1/bookings/{b['code']}/voucher", headers=H)
    assert v.status_code == 200 and v.content[:4] == b"%PDF"
    # visão da operadora traz comissão de 10%
    ob = client.get(f"/api/v1/operator/bookings/{b['code']}", headers=as_role("admin", op.id)).json()
    assert ob["commission_cents"] == 30_00 and ob["operator_amount_cents"] == 270_00


def test_public_tour_hides_private_fields(client, make_tour):
    _, tour, _ = make_tour()
    data = client.get(f"/api/v1/tours/{tour.slug}").json()
    text = str(data)
    assert "meeting_point_address" not in text and "contact" not in text and "meeting_lat" not in text
    assert data["lat"] == round(-22.97, 2)


def test_last_seat_race(client, make_tour):
    _, _, dep = make_tour(capacity=1)
    assert _book(client, dep.id).status_code == 201
    r = _book(client, dep.id)
    assert r.status_code == 409 and r.json()["error"]["code"] == "no_availability"


def test_commission_override(client, make_tour, db):
    op, _, dep = make_tour(price=100_00)
    client.patch(f"/api/v1/admin/operators/{op.id}", headers=as_role("admin"), json={"commission_rate": "0.15"})
    code = _book(client, dep.id).json()["code"]
    b = db.query(Booking).filter_by(code=code).one()
    assert b.commission_cents == 15_00 and b.operator_amount_cents == 85_00


def test_expired_hold_releases_and_late_payment(client, make_tour, db):
    _, _, dep = make_tour(capacity=1)
    code = _book(client, dep.id).json()["code"]
    pay = client.post(f"/api/v1/bookings/{code}/payments", headers=H, json={"method": "pix"}).json()
    db.execute(update(Booking).where(Booking.code == code).values(hold_expires_at=now_utc() - timedelta(minutes=1)))
    db.commit()
    assert booking_service.expire_holds(db) == 1
    db.expire_all()
    assert db.get(Departure, dep.id).seats_held == 0
    # pagamento atrasado com vaga livre: confirma
    r = client.post(f"/api/v1/dev/payments/{pay['payment']['charge_id']}/simulate", headers=H)
    assert r.json()["status"] == "confirmed"


def test_late_payment_without_seat_refunds(client, make_tour, db):
    _, _, dep = make_tour(capacity=1)
    code = _book(client, dep.id).json()["code"]
    pay = client.post(f"/api/v1/bookings/{code}/payments", headers=H, json={"method": "pix"}).json()
    db.execute(update(Booking).where(Booking.code == code).values(hold_expires_at=now_utc() - timedelta(minutes=1)))
    db.commit()
    booking_service.expire_holds(db)
    other = _book(client, dep.id).json()["code"]
    assert _pay(client, other).json()["status"] == "confirmed"
    r = client.post(f"/api/v1/dev/payments/{pay['payment']['charge_id']}/simulate", headers=H).json()
    assert r["status"] == "cancelled" and r["cancel_reason"] == "no_availability"
    assert r["refund_amount_cents"] == r["total_cents"]


def test_tourist_cancellation_policy(client, make_tour):
    _, _, dep = make_tour(days=3, policy="flexible")
    code = _book(client, dep.id).json()["code"]
    _pay(client, code)
    r = client.post(f"/api/v1/bookings/{code}/cancel", headers=H).json()
    assert r["status"] == "cancelled" and r["refund_amount_cents"] == r["total_cents"]

    _, _, dep2 = make_tour(days=3, policy="strict")
    code2 = _book(client, dep2.id).json()["code"]
    _pay(client, code2)
    r2 = client.post(f"/api/v1/bookings/{code2}/cancel", headers=H).json()
    assert r2["status"] == "cancelled" and r2["refund_amount_cents"] == 0


def test_weather_cancels_departure_and_refunds(client, make_tour, db):
    op, _, dep = make_tour(capacity=5)
    codes = [_book(client, dep.id).json()["code"] for _ in range(2)]
    for c in codes:
        _pay(client, c)
    r = client.post(f"/api/v1/operator/departures/{dep.id}/cancel", headers=as_role("admin", op.id),
                    json={"reason": "weather"})
    assert r.json()["cancelled_bookings"] == 2
    assert db.query(Refund).count() == 2
    db.expire_all()
    assert db.get(Departure, dep.id).seats_booked == 0


def test_operator_cancellation_counts(client, make_tour, db):
    op, _, dep = make_tour()
    code = _book(client, dep.id).json()["code"]
    _pay(client, code)
    client.post(f"/api/v1/operator/bookings/{code}/cancel", headers=as_role("admin", op.id))
    db.expire_all()
    assert db.get(Operator, op.id).cancellations_count == 1


def test_payouts(client, make_tour, db):
    op, _, dep = make_tour(price=200_00)
    code = _book(client, dep.id).json()["code"]
    _pay(client, code)
    db.execute(update(Booking).where(Booking.code == code)
               .values(status="completed", completed_at=now_utc() - timedelta(days=5)))
    db.commit()
    payouts = payout_service.generate(db, None)
    assert len(payouts) == 1 and payouts[0].amount_cents == 180_00
    assert payout_service.generate(db, None) == []  # não duplica


def test_bookable_cutoff(client, make_tour, db):
    _, tour, dep = make_tour(days=0, hour=0)  # saída no passado/antes do corte
    r = _book(client, dep.id)
    assert r.status_code == 409
