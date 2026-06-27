from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


TargetType = Literal["stock", "index"]
PushStatus = Literal["sent", "skipped", "failed"]


class TargetCreate(BaseModel):
    symbol: str
    name: str
    target_type: TargetType
    market: str = "CN"
    enabled: bool = True
    cooldown_minutes: int = Field(default=60, ge=0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) != 6 or not normalized.isdigit():
            raise ValueError("symbol must be a six-digit A-share or index code")
        return normalized

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name is required")
        return normalized


class TargetRead(TargetCreate):
    id: int


class MarketSnapshot(BaseModel):
    symbol: str
    name: str
    market: str
    target_type: TargetType
    last_price: float
    change_percent: float
    volume: float
    amount: float
    data_timestamp: datetime | str
    source: str
    source_url: str
    raw_payload: dict[str, Any]


class ReportContent(BaseModel):
    title: str
    summary: str
    key_points: list[str]
    evidence_refs: list[str]
    watch_items: list[str]
    risk_note: str

    def as_markdown(self) -> str:
        sections = [
            f"# {self.title}",
            self.summary,
            "## 关键点",
            *[f"- {point}" for point in self.key_points],
            "## 后续观察",
            *[f"- {item}" for item in self.watch_items],
            f"## 风险提示\n{self.risk_note}",
        ]
        return "\n\n".join(sections)
