"""Armazenamento de arquivos. Com STORAGE_* configurado, usa S3 compatível (R2, S3, MinIO).
Sem configuração (desenvolvimento), grava em ./media e a API serve em /media."""
import uuid
from pathlib import Path

from app.core.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _s3():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint or None,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
    )


def save_image(content: bytes, content_type: str, prefix: str) -> tuple[str, str]:
    """Salva e retorna (storage_key, url pública)."""
    ext = ALLOWED_IMAGE_TYPES[content_type]
    key = f"{prefix}/{uuid.uuid4().hex}.{ext}"
    if settings.storage_configured:
        _s3().put_object(Bucket=settings.storage_bucket, Key=key, Body=content, ContentType=content_type)
        base = settings.storage_public_url.rstrip("/")
        return key, f"{base}/{key}"
    path = Path(settings.media_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return key, f"{settings.api_public_url.rstrip('/')}/media/{key}"


def delete(storage_key: str) -> None:
    if not storage_key:
        return
    if settings.storage_configured:
        _s3().delete_object(Bucket=settings.storage_bucket, Key=storage_key)
        return
    path = Path(settings.media_dir) / storage_key
    if path.is_file():
        path.unlink()


def sniff_image_type(content: bytes) -> str | None:
    """Confere o tipo pelo conteúdo (não confia no header do upload)."""
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None
