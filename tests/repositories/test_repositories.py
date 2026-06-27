from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from stock_agent.app.models.tables import Base
from stock_agent.app.repositories.evidence import EvidenceRepository
from stock_agent.app.repositories.push_records import PushRecordRepository
from stock_agent.app.repositories.settings import SettingsRepository
from stock_agent.app.repositories.watch_targets import WatchTargetRepository


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_watch_target_repository_crud():
    session = make_session()
    repo = WatchTargetRepository(session)
    created = repo.create(symbol="600519", name="贵州茅台", target_type="stock")
    assert created.id is not None
    assert repo.list_enabled()[0].symbol == "600519"
    repo.delete(created.id)
    assert repo.list_enabled() == []


def test_settings_repository_upserts_values_and_secret_flag():
    session = make_session()
    repo = SettingsRepository(session)
    repo.set("server_chan_send_key", "SCTxxxx", is_secret=True)
    setting = repo.get("server_chan_send_key")
    assert setting.value == "SCTxxxx"
    assert setting.is_secret is True


def test_evidence_and_push_record_repositories_store_json_text():
    session = make_session()
    evidence = EvidenceRepository(session).create(
        symbol="600519",
        target_type="stock",
        evidence_type="market_snapshot",
        source="akshare",
        source_url="https://akshare.akfamily.xyz/",
        payload={"last_price": 1500.5},
    )
    push = PushRecordRepository(session).create(
        push_id="push_1",
        title="早报",
        content="content",
        channel="server_chan",
        status="sent",
        evidence_ids=[evidence.id],
    )
    assert push.evidence_ids == [evidence.id]
    assert PushRecordRepository(session).list_recent(limit=1)[0].push_id == "push_1"
