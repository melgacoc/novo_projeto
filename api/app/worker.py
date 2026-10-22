"""Worker Celery + agendamentos (Celery Beat). Rodar: `celery -A app.worker.celery_app worker --beat`."""
import logging
from datetime import datetime, timedelta

from celery import Celery
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import setup_logging

setup_logging()
log = logging.getLogger("app.worker")

celery_app = Celery("tur", broker=settings.redis_url, backend=None)
celery_app.conf.update(
    task_always_eager=settings.app_env == "test",
    task_ignore_result=True,
    timezone="America/Sao_Paulo",
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "expire-holds": {"task": "app.worker.expire_holds_task", "schedule": 60.0},
        "complete-bookings": {"task": "app.worker.complete_bookings_task", "schedule": 15 * 60.0},
        "generate-departures": {"task": "app.worker.generate_departures_task", "schedule": 6 * 3600.0},
        "reminders": {"task": "app.worker.send_reminders_task", "schedule": 3600.0},
        "retry-webhooks": {"task": "app.worker.reprocess_webhooks_task", "schedule": 600.0},
    },
)


@celery_app.task(name="app.worker.send_email_task", autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_email_task(to: str, subject: str, html: str, attach_voucher_booking_id: int | None = None) -> None:
    from app.models import Booking
    from app.services.email_service import send_email_now
    from app.services.voucher import render_voucher

    attachments = []
    if attach_voucher_booking_id:
        with SessionLocal() as db:
            booking = db.get(Booking, attach_voucher_booking_id)
            if booking:
                attachments.append((f"voucher-{booking.code}.pdf", render_voucher(db, booking), "application/pdf"))
    send_email_now(to, subject, html, attachments)


@celery_app.task(name="app.worker.expire_holds_task")
def expire_holds_task() -> int:
    from app.services.booking_service import expire_holds

    with SessionLocal() as db:
        return expire_holds(db)


@celery_app.task(name="app.worker.complete_bookings_task")
def complete_bookings_task() -> int:
    from app.services.booking_service import complete_finished

    with SessionLocal() as db:
        return complete_finished(db)


@celery_app.task(name="app.worker.reprocess_webhooks_task")
def reprocess_webhooks_task() -> int:
    from app.services.booking_service import reprocess_failed_webhooks

    with SessionLocal() as db:
        return reprocess_failed_webhooks(db)


@celery_app.task(name="app.worker.generate_departures_task")
def generate_departures_task() -> int:
    from app.services.schedule_service import generate_all

    with SessionLocal() as db:
        return generate_all(db)


@celery_app.task(name="app.worker.send_reminders_task")
def send_reminders_task() -> int:
    """Lembrete para as saídas que começam entre 20 e 21 horas a partir de agora (roda de hora em hora)."""
    from app.core.redis import redis_client
    from app.models import Booking, Departure
    from app.services import email_service
    from app.services.booking_service import fmt_when

    now = datetime.now().astimezone()
    sent = 0
    with SessionLocal() as db:
        rows = db.execute(
            select(Booking, Departure)
            .join(Departure, Departure.id == Booking.departure_id)
            .where(
                Booking.status == "confirmed",
                Departure.starts_at >= now + timedelta(hours=20),
                Departure.starts_at < now + timedelta(hours=21),
            )
        ).all()
        for booking, dep in rows:
            if not redis_client.set(f"reminder:{booking.id}", "1", nx=True, ex=3 * 86400):
                continue
            subject, html = email_service.render(
                "reminder", booking.locale, title=booking.snapshot.get("title", ""), code=booking.code,
                when=fmt_when(dep.starts_at),
            )
            email_service.enqueue_email(booking.contact_email, subject, html, attach_voucher_booking_id=booking.id)
            sent += 1
    return sent
