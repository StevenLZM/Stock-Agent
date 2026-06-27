from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from stock_agent.app.domain.schemas import MarketSnapshot, ReportContent
from stock_agent.app.models.tables import Base
from stock_agent.app.repositories.evidence import EvidenceRepository
from stock_agent.app.repositories.push_records import PushRecordRepository
from stock_agent.app.repositories.watch_targets import WatchTargetRepository
from stock_agent.app.services.reports import MorningReportService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class FakeMarketProvider:
    def fetch_snapshot(self, symbol, target_type):
        return MarketSnapshot(
            symbol=symbol,
            name="贵州茅台",
            market="CN",
            target_type=target_type,
            last_price=1500.5,
            change_percent=1.2,
            volume=100,
            amount=2000,
            data_timestamp="2026-06-27T09:30:00+08:00",
            source="fake",
            source_url="https://example.test",
            raw_payload={"symbol": symbol},
        )


class FakeLLM:
    def generate_morning_report(self, evidence, quality="pro"):
        return ReportContent(
            title="关注标的早报",
            summary="贵州茅台 最新价 1500.5，涨跌幅 1.2%",
            key_points=["贵州茅台 最新价 1500.5"],
            evidence_refs=["600519"],
            watch_items=["观察成交量变化"],
            risk_note="以上仅为信息整理，不构成投资建议。",
        )


class UnsafeLLM:
    def generate_morning_report(self, evidence, quality="pro"):
        return ReportContent(
            title="危险早报",
            summary="建议买入贵州茅台",
            key_points=["必涨"],
            evidence_refs=["600519"],
            watch_items=["观察"],
            risk_note="以上仅为信息整理，不构成投资建议。",
        )


@dataclass
class FakePushResult:
    success: bool = True
    error_message: str = ""


class FakePushProvider:
    def send(self, title, content):
        return FakePushResult()


def test_morning_report_service_stores_evidence_and_push_record():
    session = make_session()
    WatchTargetRepository(session).create("600519", "贵州茅台", "stock")
    session.commit()
    service = MorningReportService(
        session=session,
        targets=WatchTargetRepository(session),
        evidence=EvidenceRepository(session),
        push_records=PushRecordRepository(session),
        market_provider=FakeMarketProvider(),
        llm=FakeLLM(),
        push_provider=FakePushProvider(),
    )
    record = service.run()
    assert record.status == "sent"
    assert len(EvidenceRepository(session).list_recent(limit=10)) == 1
    assert PushRecordRepository(session).list_recent(limit=1)[0].title == "关注标的早报"


def test_morning_report_service_skips_push_when_provider_missing():
    session = make_session()
    WatchTargetRepository(session).create("600519", "贵州茅台", "stock")
    session.commit()
    service = MorningReportService(
        session=session,
        targets=WatchTargetRepository(session),
        evidence=EvidenceRepository(session),
        push_records=PushRecordRepository(session),
        market_provider=FakeMarketProvider(),
        llm=FakeLLM(),
        push_provider=None,
    )
    record = service.run()
    assert record.status == "skipped"
    assert record.error_message == "SERVER_CHAN_SEND_KEY is not configured"


def test_morning_report_service_sends_llm_content_without_guardrail_degrade():
    session = make_session()
    WatchTargetRepository(session).create("600519", "贵州茅台", "stock")
    session.commit()
    service = MorningReportService(
        session=session,
        targets=WatchTargetRepository(session),
        evidence=EvidenceRepository(session),
        push_records=PushRecordRepository(session),
        market_provider=FakeMarketProvider(),
        llm=UnsafeLLM(),
        push_provider=FakePushProvider(),
    )
    record = service.run()
    assert record.status == "sent"
    assert "建议买入" in record.content
