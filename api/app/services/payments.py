"""Gateway de pagamento: interface comum + implementação "fake" para desenvolvimento.

Para integrar um gateway real (Pagar.me, Mercado Pago, Asaas, Iugu, Stripe Connect), crie uma classe
que implemente `PaymentGateway` e registre em `_GATEWAYS`. Ver docs/integracoes.md.
"""
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.core.config import settings
from app.core.errors import AppError


@dataclass
class ChargeResult:
    charge_id: str
    status: str  # pending | approved | failed
    pix_qr_code: str | None = None
    pix_expires_at: datetime | None = None
    checkout_url: str | None = None
    fee_cents: int = 0
    raw: dict = field(default_factory=dict)


@dataclass
class GatewayEvent:
    event_id: str
    type: str  # payment.approved | payment.failed | refund.completed | chargeback
    charge_id: str
    raw: dict


class PaymentGateway:
    name = "base"

    def create_charge(
        self,
        *,
        reference: str,
        method: str,
        amount_cents: int,
        expires_at: datetime,
        customer: dict,
        description: str,
        idempotency_key: str,
    ) -> ChargeResult:
        raise NotImplementedError

    def refund(self, *, charge_id: str, amount_cents: int) -> str:
        """Estorna (total ou parcial). Retorna o id do estorno no gateway."""
        raise NotImplementedError

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> GatewayEvent:
        """Valida a assinatura e normaliza o evento. Lança AppError(401) se a assinatura for inválida."""
        raise NotImplementedError


class FakeGateway(PaymentGateway):
    """Simula um gateway. Toda cobrança nasce pendente; a aprovação vem por um "webhook" assinado,
    disparado pela rota de desenvolvimento `/api/v1/dev/payments/{charge_id}/simulate`."""

    name = "fake"

    def create_charge(self, *, reference, method, amount_cents, expires_at, customer, description, idempotency_key):
        charge_id = f"fake_{uuid.uuid4().hex[:16]}"
        fee = round(amount_cents * (0.0099 if method == "pix" else 0.0499))
        pix = None
        if method == "pix":
            pix = f"00020126580014BR.GOV.BCB.PIX0136{charge_id}5204000053039865406{amount_cents / 100:.2f}5802BR5903TUR6009RIODEJANE62070503***6304FAKE"
        return ChargeResult(
            charge_id=charge_id,
            status="pending",
            pix_qr_code=pix,
            pix_expires_at=expires_at if method == "pix" else None,
            checkout_url=None,
            fee_cents=fee,
            raw={"reference": reference, "method": method, "amount": amount_cents},
        )

    def refund(self, *, charge_id, amount_cents):
        return f"fake_refund_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def sign(body: bytes) -> str:
        return hmac.new(settings.payment_webhook_secret.encode(), body, hashlib.sha256).hexdigest()

    def parse_webhook(self, headers, body):
        signature = headers.get("x-signature", "")
        if not hmac.compare_digest(signature, self.sign(body)):
            raise AppError(401, "invalid_signature", "Assinatura do webhook inválida")
        data = json.loads(body)
        return GatewayEvent(event_id=data["id"], type=data["type"], charge_id=data["charge_id"], raw=data)

    def build_event(self, charge_id: str, event_type: str) -> tuple[bytes, dict[str, str]]:
        body = json.dumps({"id": f"evt_{uuid.uuid4().hex}", "type": event_type, "charge_id": charge_id}).encode()
        return body, {"x-signature": self.sign(body)}


_GATEWAYS: dict[str, type[PaymentGateway]] = {"fake": FakeGateway}


def get_gateway(name: str | None = None) -> PaymentGateway:
    name = name or settings.payment_gateway
    cls = _GATEWAYS.get(name)
    if not cls:
        raise AppError(503, "gateway_not_available", f"Gateway '{name}' não implementado. Ver docs/integracoes.md")
    return cls()
