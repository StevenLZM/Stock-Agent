import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from stock_agent.app.models.tables import EvidenceItem


class EvidenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        symbol: str,
        target_type: str,
        evidence_type: str,
        source: str,
        source_url: str,
        payload: dict[str, Any],
        data_timestamp: datetime | str | None = None,
    ) -> EvidenceItem:
        evidence = EvidenceItem(
            symbol=symbol,
            target_type=target_type,
            evidence_type=evidence_type,
            source=source,
            source_url=source_url,
            data_timestamp=_normalize_datetime(data_timestamp),
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
        self.session.add(evidence)
        self.session.flush()
        return evidence

    def list_recent(self, limit: int) -> list[EvidenceItem]:
        statement = select(EvidenceItem).order_by(EvidenceItem.created_at.desc(), EvidenceItem.id.desc()).limit(limit)
        return list(self.session.scalars(statement).all())


def _normalize_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("data_timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)
