from sqlalchemy.orm import Session

from app.models import AuditLog


def _clean(values: dict | None) -> dict | None:
    if values is None:
        return None
    return {k: (str(v) if v is not None and not isinstance(v, (int, float, bool, str, list, dict)) else v)
            for k, v in values.items()}


def audit(
    db: Session,
    user_id: int | None,
    entity: str,
    entity_id: int | str,
    action: str,
    old: dict | None = None,
    new: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            entity=entity,
            entity_id=str(entity_id),
            action=action,
            old_values=_clean(old),
            new_values=_clean(new),
        )
    )
