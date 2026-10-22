"""Preço por faixa etária e temporada (RN02, RN03). Tudo calculado no servidor."""
from dataclasses import dataclass
from datetime import date

from app.core.errors import bad_request
from app.models import Tour, TourPriceCategory


def price_on(category: TourPriceCategory, on: date) -> int | None:
    for p in category.prices:
        if p.valid_from <= on and (p.valid_to is None or on <= p.valid_to):
            return p.price_cents
    return None


def label(category: TourPriceCategory, locale: str) -> str:
    return getattr(category, f"label_{locale}", "") or category.label_pt or category.code


@dataclass
class QuoteLine:
    code: str
    label: str
    quantity: int
    unit_price_cents: int

    @property
    def total_cents(self) -> int:
        return self.quantity * self.unit_price_cents


@dataclass
class Quote:
    lines: list[QuoteLine]
    pax_total: int
    subtotal_cents: int


def quote(tour: Tour, on: date, quantities: dict[str, int], locale: str) -> Quote:
    cats = {c.code: c for c in tour.price_categories}
    lines: list[QuoteLine] = []
    for code, qty in quantities.items():
        if qty <= 0:
            continue
        cat = cats.get(code)
        if not cat:
            raise bad_request("invalid_category", f"Categoria de preço inválida: {code}")
        unit = price_on(cat, on)
        if unit is None:
            raise bad_request("no_price", f"Sem preço vigente para {code} nesta data")
        lines.append(QuoteLine(code=code, label=label(cat, locale), quantity=qty, unit_price_cents=unit))
    pax = sum(line.quantity for line in lines)
    if pax == 0:
        raise bad_request("no_pax", "Informe pelo menos uma pessoa")
    if pax < tour.min_pax_per_booking or pax > tour.max_pax_per_booking:
        raise bad_request(
            "pax_out_of_range",
            f"Número de pessoas deve ficar entre {tour.min_pax_per_booking} e {tour.max_pax_per_booking}",
        )
    return Quote(lines=lines, pax_total=pax, subtotal_cents=sum(line.total_cents for line in lines))


def recompute_from_price(tour: Tour, today: date) -> None:
    """Menor preço de adulto vigente hoje (ou de qualquer categoria, se não houver adulto)."""
    candidates: list[int] = []
    adults = [c for c in tour.price_categories if c.code == "adult"]
    for cat in adults or tour.price_categories:
        p = price_on(cat, today)
        if p is None:
            future = [x.price_cents for x in cat.prices if x.valid_from > today]
            p = min(future) if future else None
        if p is not None:
            candidates.append(p)
    tour.from_price_cents = min(candidates) if candidates else None
