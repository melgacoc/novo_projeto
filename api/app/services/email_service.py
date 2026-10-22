"""Envio de e-mail por SMTP (qualquer provedor). Templates simples nos 3 idiomas.

O envio real acontece no worker (`app.worker.send_email_task`). Sem SMTP configurado, o e-mail só vai para o log.
"""
import logging
import smtplib
from email.message import EmailMessage
from html import escape

from app.core.config import settings

log = logging.getLogger("app.email")


def send_email_now(to: str, subject: str, html: str, attachments: list[tuple[str, bytes, str]] | None = None) -> None:
    if not settings.smtp_configured:
        log.info("SMTP não configurado; e-mail não enviado: to=%s subject=%s", to, subject)
        return
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("Abra este e-mail em um cliente que suporte HTML.")
    msg.add_alternative(html, subtype="html")
    for filename, content, mime in attachments or []:
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def enqueue_email(to: str, subject: str, html: str, attach_voucher_booking_id: int | None = None) -> None:
    """Coloca o e-mail na fila do worker. Se a fila estiver indisponível, envia direto."""
    from app.worker import send_email_task

    try:
        send_email_task.delay(to, subject, html, attach_voucher_booking_id)
    except Exception:  # noqa: BLE001
        log.warning("fila indisponível; enviando e-mail de forma síncrona", exc_info=True)
        try:
            send_email_task(to, subject, html, attach_voucher_booking_id)
        except Exception:  # noqa: BLE001
            log.exception("falha ao enviar e-mail")


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
T = {
    "login_code": {
        "pt": ("Seu código de acesso: {code}", "Use o código <b>{code}</b> para entrar. Ele vale por 10 minutos."),
        "es": ("Tu código de acceso: {code}", "Usa el código <b>{code}</b> para ingresar. Vale por 10 minutos."),
        "en": ("Your access code: {code}", "Use the code <b>{code}</b> to sign in. It is valid for 10 minutes."),
    },
    "booking_confirmed": {
        "pt": ("Reserva confirmada: {title}", "Sua reserva <b>{code}</b> para <b>{title}</b> em {when} está confirmada. O voucher, com o ponto de encontro, está em anexo e em <a href=\"{link}\">Minhas reservas</a>."),
        "es": ("Reserva confirmada: {title}", "Tu reserva <b>{code}</b> para <b>{title}</b> el {when} está confirmada. El voucher, con el punto de encuentro, va adjunto y en <a href=\"{link}\">Mis reservas</a>."),
        "en": ("Booking confirmed: {title}", "Your booking <b>{code}</b> for <b>{title}</b> on {when} is confirmed. The voucher, with the meeting point, is attached and in <a href=\"{link}\">My bookings</a>."),
    },
    "booking_cancelled": {
        "pt": ("Reserva cancelada: {title}", "Sua reserva <b>{code}</b> para <b>{title}</b> em {when} foi cancelada ({reason}). Reembolso: <b>{refund}</b>."),
        "es": ("Reserva cancelada: {title}", "Tu reserva <b>{code}</b> para <b>{title}</b> el {when} fue cancelada ({reason}). Reembolso: <b>{refund}</b>."),
        "en": ("Booking cancelled: {title}", "Your booking <b>{code}</b> for <b>{title}</b> on {when} was cancelled ({reason}). Refund: <b>{refund}</b>."),
    },
    "reminder": {
        "pt": ("Amanhã: {title}", "Lembrete: sua reserva <b>{code}</b> para <b>{title}</b> é em {when}. Confira o ponto de encontro no voucher."),
        "es": ("Mañana: {title}", "Recordatorio: tu reserva <b>{code}</b> para <b>{title}</b> es el {when}. Revisa el punto de encuentro en el voucher."),
        "en": ("Tomorrow: {title}", "Reminder: your booking <b>{code}</b> for <b>{title}</b> is on {when}. Check the meeting point on the voucher."),
    },
}

REASONS = {
    "tourist": {"pt": "a seu pedido", "es": "a tu pedido", "en": "at your request"},
    "weather": {"pt": "condições do tempo", "es": "condiciones climáticas", "en": "weather conditions"},
    "operator": {"pt": "cancelado pela operadora", "es": "cancelado por el operador", "en": "cancelled by the operator"},
    "no_availability": {"pt": "sem vagas no momento do pagamento", "es": "sin cupos al momento del pago", "en": "no seats left when the payment arrived"},
    "admin": {"pt": "cancelado pela plataforma", "es": "cancelado por la plataforma", "en": "cancelled by the platform"},
}


def render(key: str, locale: str, **params) -> tuple[str, str]:
    locale = locale if locale in ("pt", "es", "en") else "pt"
    subject, body = T[key][locale]
    safe = {k: escape(str(v)) for k, v in params.items()}
    if "link" in params:
        safe["link"] = params["link"]
    html = (
        "<div style=\"font-family:Arial,sans-serif;max-width:560px;margin:auto;padding:24px\">"
        f"<h2 style=\"color:#0284c7\">{escape(settings.app_name)}</h2><p>{body.format(**safe)}</p></div>"
    )
    return subject.format(**params), html


def reason_text(reason: str | None, locale: str) -> str:
    return REASONS.get(reason or "", {}).get(locale, reason or "")
