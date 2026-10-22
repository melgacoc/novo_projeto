import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://tur:tur@localhost:5433/tur_test"
)
os.environ["SMTP_HOST"] = ""
os.environ["AUTH_ENABLED"] = "false"

from datetime import datetime, time, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Departure, Operator, Tour, TourPrice, TourPriceCategory, TourTranslation  # noqa: E402
from app.seed import seed_base  # noqa: E402
from app.services import pricing  # noqa: E402
from app.services.catalog_service import set_locations  # noqa: E402
from app.services.schedule_service import TZ, today_local  # noqa: E402


@pytest.fixture(autouse=True)
def _db():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_base(db)
    settings.auth_enabled = False
    yield
    settings.auth_enabled = False


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client():
    return TestClient(app)


def as_role(role: str, operator_id: int | None = None) -> dict:
    h = {"X-Dev-User-Role": role}
    if operator_id:
        h["X-Operator-Id"] = str(operator_id)
    return h


@pytest.fixture
def make_tour(db):
    """Cria operadora ativa + passeio publicado + uma saída daqui a `days` dias."""

    def _make(capacity: int = 10, days: int = 3, policy: str = "flexible", price: int = 100_00,
              operator: Operator | None = None, hour: int = 9):
        if operator is None:
            operator = Operator(public_name="Op Teste", trade_name="Op Teste Ltda", status="active",
                                contact_phone="+5521911112222", contact_email="op@teste.local")
            db.add(operator)
            db.flush()
        tour = Tour(operator_id=operator.id, slug=f"t-{operator.id}-{datetime.now().timestamp()}",
                    status="published", duration_minutes=120, booking_cutoff_minutes=60,
                    cancellation_policy=policy, max_pax_per_booking=10)
        set_locations(tour, -22.97, -43.18)
        for loc in ("pt", "es", "en"):
            tour.translations.append(TourTranslation(locale=loc, title=f"Passeio {loc}", summary="s", description="d"))
        cat = TourPriceCategory(code="adult", min_age=0, max_age=120, label_pt="Adulto")
        cat.prices.append(TourPrice(price_cents=price, valid_from=today_local() - timedelta(days=1)))
        tour.price_categories.append(cat)
        db.add(tour)
        db.flush()
        pricing.recompute_from_price(tour, today_local())
        dep = Departure(tour_id=tour.id, capacity=capacity, status="open",
                        starts_at=datetime.combine(today_local() + timedelta(days=days), time(hour, 0), tzinfo=TZ))
        db.add(dep)
        db.commit()
        return operator, tour, dep

    return _make
