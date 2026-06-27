from uuid import uuid4

from sqlalchemy.orm import Session

from stock_agent.app.domain.schemas import MarketSnapshot, ReportContent
from stock_agent.app.models.tables import PushRecord
from stock_agent.app.repositories.evidence import EvidenceRepository
from stock_agent.app.repositories.push_records import PushRecordRepository
from stock_agent.app.repositories.watch_targets import WatchTargetRepository
from stock_agent.app.services.guardrail import Guardrail


class MorningReportService:
    def __init__(
        self,
        session: Session,
        targets: WatchTargetRepository,
        evidence: EvidenceRepository,
        push_records: PushRecordRepository,
        market_provider,
        llm,
        push_provider=None,
        guardrail: Guardrail | None = None,
    ):
        self.session = session
        self.targets = targets
        self.evidence = evidence
        self.push_records = push_records
        self.market_provider = market_provider
        self.llm = llm
        self.push_provider = push_provider
        self.guardrail = guardrail or Guardrail()

    def run(self) -> PushRecord:
        try:
            snapshots = self._collect_snapshots()
            evidence_ids = [self._store_evidence(snapshot).id for snapshot in snapshots]
            report, status = self._build_report(snapshots)
            content = report.as_markdown()
            push_error = None

            if self.push_provider is None:
                status = "skipped"
                push_error = "SERVER_CHAN_SEND_KEY is not configured"
            else:
                push_result = self.push_provider.send(title=report.title, content=content)
                if not push_result.success:
                    status = "failed"
                    push_error = push_result.error_message

            record = self.push_records.create(
                push_id=f"push_{uuid4().hex}",
                title=report.title,
                content=content,
                channel="server_chan",
                status=status,
                evidence_ids=evidence_ids,
                error_message=push_error,
            )
            self.session.commit()
            return record
        except Exception:
            self.session.rollback()
            raise

    def _collect_snapshots(self) -> list[MarketSnapshot]:
        return [self.market_provider.fetch_snapshot(target.symbol, target.target_type) for target in self.targets.list_enabled()]

    def _store_evidence(self, snapshot: MarketSnapshot):
        return self.evidence.create(
            symbol=snapshot.symbol,
            target_type=snapshot.target_type,
            evidence_type="market_snapshot",
            source=snapshot.source,
            source_url=snapshot.source_url,
            payload=snapshot.model_dump(mode="json"),
            data_timestamp=snapshot.data_timestamp,
        )

    def _build_report(self, snapshots: list[MarketSnapshot]) -> tuple[ReportContent, str]:
        try:
            report = self.llm.generate_morning_report(snapshots, quality="pro")
        except Exception:
            return self._fallback_report(snapshots), "degraded"

        allowed_numbers = self._allowed_numbers(snapshots)
        guardrail_result = self.guardrail.validate(report, allowed_numbers=allowed_numbers)
        if not guardrail_result.passed:
            return self._fallback_report(snapshots), "degraded"
        return report, "sent"

    def _fallback_report(self, snapshots: list[MarketSnapshot]) -> ReportContent:
        key_points = [
            f"{snapshot.name} 最新价 {snapshot.last_price}，涨跌幅 {snapshot.change_percent}%"
            for snapshot in snapshots
        ]
        return ReportContent(
            title="关注标的早报",
            summary="以下为结构化行情事实摘要。",
            key_points=key_points,
            evidence_refs=[snapshot.symbol for snapshot in snapshots],
            watch_items=["继续观察价格、成交量和后续公告变化。"],
            risk_note="以上仅为信息整理，不构成投资建议。",
        )

    def _allowed_numbers(self, snapshots: list[MarketSnapshot]) -> set[str]:
        allowed: set[str] = set()
        for snapshot in snapshots:
            allowed.add(str(snapshot.last_price))
            allowed.add(str(snapshot.change_percent))
            allowed.add(str(snapshot.volume))
            allowed.add(str(snapshot.amount))
        return allowed
