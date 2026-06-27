from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from stock_agent.app.core.database import engine_from_url, sessionmaker_for_url
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


def test_repositories_do_not_commit_so_services_control_transactions():
    session = make_session()
    targets = WatchTargetRepository(session)
    settings = SettingsRepository(session)
    evidence_repo = EvidenceRepository(session)
    push_records = PushRecordRepository(session)

    target = targets.create(symbol="600519", name="贵州茅台", target_type="stock")
    settings.set("server_chan_send_key", "SCTxxxx", is_secret=True)
    evidence = evidence_repo.create(
        symbol="600519",
        target_type="stock",
        evidence_type="market_snapshot",
        source="akshare",
        source_url="https://akshare.akfamily.xyz/",
        payload={"last_price": 1500.5},
    )
    push_records.create(
        push_id="push_rollback",
        title="早报",
        content="content",
        channel="server_chan",
        status="sent",
        evidence_ids=[evidence.id],
    )

    assert target.id is not None
    assert evidence.id is not None

    session.rollback()

    assert targets.list_enabled() == []
    assert settings.get("server_chan_send_key") is None
    assert evidence_repo.list_recent(limit=10) == []
    assert push_records.list_recent(limit=10) == []


def test_evidence_repository_normalizes_iso_timestamp_strings():
    session = make_session()
    evidence = EvidenceRepository(session).create(
        symbol="600519",
        target_type="stock",
        evidence_type="market_snapshot",
        source="akshare",
        source_url="https://akshare.akfamily.xyz/",
        payload={"last_price": 1500.5},
        data_timestamp="2026-06-27T09:30:00+08:00",
    )
    assert evidence.data_timestamp is not None
    assert evidence.data_timestamp.year == 2026


def test_database_helpers_cache_engines_and_sessionmakers():
    database_url = "sqlite:///:memory:"
    assert engine_from_url(database_url) is engine_from_url(database_url)
    assert sessionmaker_for_url(database_url) is sessionmaker_for_url(database_url)


def test_alembic_initial_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {"watch_targets", "app_settings", "evidence_items", "push_records"}.issubset(tables)

    command.downgrade(config, "base")

    tables_after_downgrade = set(inspect(engine).get_table_names())
    assert "watch_targets" not in tables_after_downgrade
