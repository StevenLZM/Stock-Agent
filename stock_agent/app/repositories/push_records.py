import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from stock_agent.app.models.tables import PushRecord


class PushRecordRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        push_id: str,
        title: str,
        content: str,
        channel: str,
        status: str,
        evidence_ids: list[int],
        error_message: str | None = None,
        sent_at: datetime | None = None,
    ) -> PushRecord:
        record = PushRecord(
            push_id=push_id,
            title=title,
            content=content,
            channel=channel,
            status=status,
            evidence_ids_json=json.dumps(evidence_ids, ensure_ascii=False),
            error_message=error_message,
            sent_at=sent_at,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def list_recent(self, limit: int) -> list[PushRecord]:
        statement = select(PushRecord).order_by(PushRecord.created_at.desc(), PushRecord.id.desc()).limit(limit)
        return list(self.session.scalars(statement).all())
