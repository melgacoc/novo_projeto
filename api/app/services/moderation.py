"""Sinaliza dados de contato em textos públicos (proteção contra desintermediação, RN10).
Não bloqueia: gera alertas para o admin revisar antes de publicar."""
import re

PATTERNS = {
    "phone": re.compile(r"(\+?\d[\d\s().-]{7,}\d)"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "url": re.compile(r"(https?://|www\.)\S+|\b[\w-]+\.(com|com\.br|net|org|tur\.br|br)\b", re.I),
    "handle": re.compile(r"(?<![\w.])@[A-Za-z0-9_.]{3,}"),
    "whatsapp": re.compile(r"\b(whats\s?app|wpp|zap)\b", re.I),
}


def find_contact_flags(texts: dict[str, str]) -> list[dict]:
    flags = []
    for field, text in texts.items():
        if not text:
            continue
        for kind, rx in PATTERNS.items():
            m = rx.search(text)
            if m:
                flags.append({"field": field, "kind": kind, "match": m.group(0)[:60]})
    return flags
