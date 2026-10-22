"""Voucher em PDF (PT/ES/EN) com QR do código da reserva, ponto de encontro exato e contato da operadora."""
from datetime import datetime
from io import BytesIO

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Booking, Operator, Tour
from app.services.booking_service import fmt_money, fmt_when
from app.services.catalog_service import tour_text

L = {
    "pt": {"voucher": "Voucher", "code": "Código", "when": "Data e hora", "pax": "Pessoas", "total": "Total pago",
           "meeting": "Ponto de encontro", "operator": "Operadora", "contact": "Contato", "fees": "Taxas pagas no local",
           "policy": "Política de cancelamento", "show": "Apresente este voucher (impresso ou no celular) no embarque."},
    "es": {"voucher": "Voucher", "code": "Código", "when": "Fecha y hora", "pax": "Personas", "total": "Total pagado",
           "meeting": "Punto de encuentro", "operator": "Operador", "contact": "Contacto", "fees": "Tasas pagadas en el lugar",
           "policy": "Política de cancelación", "show": "Presenta este voucher (impreso o en el celular) al embarcar."},
    "en": {"voucher": "Voucher", "code": "Code", "when": "Date and time", "pax": "People", "total": "Total paid",
           "meeting": "Meeting point", "operator": "Operator", "contact": "Contact", "fees": "Fees paid on site",
           "policy": "Cancellation policy", "show": "Show this voucher (printed or on your phone) when boarding."},
}
POLICY = {
    "pt": {"flexible": "Reembolso integral até 24 h antes", "moderate": "Reembolso integral até 48 h antes", "strict": "Sem reembolso"},
    "es": {"flexible": "Reembolso total hasta 24 h antes", "moderate": "Reembolso total hasta 48 h antes", "strict": "Sin reembolso"},
    "en": {"flexible": "Full refund up to 24 h before", "moderate": "Full refund up to 48 h before", "strict": "Non-refundable"},
}


def render_voucher(db: Session, booking: Booking) -> bytes:
    loc = booking.locale if booking.locale in L else "pt"
    t = L[loc]
    tour = db.get(Tour, booking.tour_id)
    operator = db.get(Operator, booking.operator_id)
    text = tour_text(tour, loc)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 25 * mm
    c.setFillColorRGB(0.01, 0.52, 0.78)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, y, f"{settings.app_name} · {t['voucher']}")
    c.setFillColorRGB(0, 0, 0)

    qr = QrCodeWidget(booking.code)
    b = qr.getBounds()
    size = 38 * mm
    d = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0, size / (b[3] - b[1]), 0, 0])
    d.add(qr)
    renderPDF.draw(d, c, w - 20 * mm - size, h - 20 * mm - size)

    y -= 14 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, (text.title or booking.snapshot.get("title", ""))[:70])
    y -= 10 * mm

    def row(label: str, value: str) -> None:
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y, label)
        c.setFont("Helvetica", 10)
        for i, line in enumerate(_wrap(value, 85)):
            c.drawString(65 * mm, y - i * 5 * mm, line)
            last = i
        y -= (last + 1) * 5 * mm + 3 * mm

    pax = ", ".join(f"{i.quantity}× {i.label}" for i in booking.items)
    row(t["code"], booking.code)
    row(t["when"], fmt_when(datetime.fromisoformat(booking.snapshot["starts_at"])))
    row(t["pax"], f"{booking.pax_total} ({pax})")
    row(t["total"], fmt_money(booking.total_cents))
    meeting = tour.meeting_point_address or ""
    if text.meeting_point_details:
        meeting = f"{meeting} — {text.meeting_point_details}" if meeting else text.meeting_point_details
    row(t["meeting"], meeting or "-")
    if tour.meeting_lat is not None:
        row("Maps", f"https://www.google.com/maps?q={tour.meeting_lat},{tour.meeting_lng}")
    row(t["operator"], operator.trade_name)
    row(t["contact"], " · ".join(x for x in [operator.contact_phone, operator.contact_email] if x) or "-")
    if tour.on_site_fees_note:
        row(t["fees"], tour.on_site_fees_note)
    row(t["policy"], POLICY[loc].get(booking.snapshot.get("cancellation_policy", "flexible"), ""))

    y -= 6 * mm
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(20 * mm, y, t["show"])
    c.showPage()
    c.save()
    return buf.getvalue()


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for word in words:
        if len(cur) + len(word) + 1 > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    lines.append(cur)
    return lines or [""]
