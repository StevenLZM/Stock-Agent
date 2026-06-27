from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from stock_agent.app.core.config import Settings
from stock_agent.app.core.database import get_session
from stock_agent.app.core.redaction import redact_secret
from stock_agent.app.models.tables import Base
from stock_agent.app.providers.akshare_market_data import AKShareMarketDataProvider
from stock_agent.app.providers.deepseek_llm import DeepSeekLLMProvider
from stock_agent.app.providers.server_chan import ServerChanProvider
from stock_agent.app.repositories.evidence import EvidenceRepository
from stock_agent.app.repositories.push_records import PushRecordRepository
from stock_agent.app.repositories.settings import SettingsRepository
from stock_agent.app.repositories.watch_targets import WatchTargetRepository
from stock_agent.app.services.reports import MorningReportService


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "web" / "templates"))


def get_settings() -> Settings:
    return Settings()


def ensure_tables(session: Session) -> None:
    Base.metadata.create_all(bind=session.get_bind())


def session_dependency():
    yield from get_session()


def build_morning_report_service(session: Session, settings: Settings) -> MorningReportService:
    settings_repository = SettingsRepository(session)
    pro_model = _stored_setting_value(settings_repository, "deepseek_pro_model", settings.deepseek_pro_model)
    flash_model = _stored_setting_value(settings_repository, "deepseek_flash_model", settings.deepseek_flash_model)
    push_provider = ServerChanProvider(settings.server_chan_send_key) if settings.server_chan_send_key else None
    return MorningReportService(
        session=session,
        targets=WatchTargetRepository(session),
        evidence=EvidenceRepository(session),
        push_records=PushRecordRepository(session),
        market_provider=AKShareMarketDataProvider(),
        llm=DeepSeekLLMProvider(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            pro_model=pro_model,
            flash_model=flash_model,
        ),
        push_provider=push_provider,
    )


def _stored_setting_value(repository: SettingsRepository, key: str, default: str) -> str:
    setting = repository.get(key)
    if setting is None or setting.value in {None, ""}:
        return default
    return str(setting.value)


def _record_manual_run_error(session: Session, settings: Settings, status: str, error_message: str) -> None:
    safe_error = _redact_configured_secrets(error_message, settings)
    PushRecordRepository(session).create(
        push_id=f"push_{uuid4().hex}",
        title="关注标的早报",
        content=safe_error,
        channel="server_chan",
        status=status,
        evidence_ids=[],
        error_message=safe_error,
    )
    session.commit()


def _redact_configured_secrets(message: str, settings: Settings) -> str:
    safe_message = message
    for secret in (settings.deepseek_api_key, settings.server_chan_send_key):
        if secret:
            safe_message = safe_message.replace(secret, redact_secret(secret))
    return safe_message


@router.get("/")
def dashboard(request: Request, session: Session = Depends(session_dependency)):
    ensure_tables(session)
    targets = WatchTargetRepository(session).list_enabled()
    pushes = PushRecordRepository(session).list_recent(limit=5)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"targets": targets, "pushes": pushes, "settings": Settings()},
    )


@router.get("/targets")
def targets_page(request: Request, session: Session = Depends(session_dependency)):
    ensure_tables(session)
    targets = WatchTargetRepository(session).list_enabled()
    return templates.TemplateResponse(request, "targets.html", {"targets": targets})


@router.post("/targets")
def create_target(
    symbol: str = Form(...),
    name: str = Form(...),
    target_type: str = Form(...),
    session: Session = Depends(session_dependency),
):
    ensure_tables(session)
    WatchTargetRepository(session).create(symbol=symbol, name=name, target_type=target_type)
    session.commit()
    return RedirectResponse("/targets", status_code=303)


@router.post("/targets/{target_id}/delete")
def delete_target(target_id: int, session: Session = Depends(session_dependency)):
    ensure_tables(session)
    WatchTargetRepository(session).delete(target_id)
    session.commit()
    return RedirectResponse("/targets", status_code=303)


@router.get("/settings")
def settings_page(request: Request, session: Session = Depends(session_dependency)):
    ensure_tables(session)
    settings = Settings()
    stored_pro_model = SettingsRepository(session).get("deepseek_pro_model")
    stored_flash_model = SettingsRepository(session).get("deepseek_flash_model")
    context = {
        "deepseek_pro_model": stored_pro_model.value if stored_pro_model else settings.deepseek_pro_model,
        "deepseek_flash_model": stored_flash_model.value if stored_flash_model else settings.deepseek_flash_model,
    }
    return templates.TemplateResponse(request, "settings.html", context)


@router.post("/settings")
def save_settings(
    deepseek_pro_model: str = Form(...),
    deepseek_flash_model: str = Form(...),
    session: Session = Depends(session_dependency),
):
    ensure_tables(session)
    settings = SettingsRepository(session)
    settings.set("deepseek_pro_model", deepseek_pro_model)
    settings.set("deepseek_flash_model", deepseek_flash_model)
    session.commit()
    return RedirectResponse("/settings", status_code=303)


@router.post("/channels/server-chan/test")
def test_server_chan():
    return RedirectResponse("/settings", status_code=303)


@router.post("/reports/morning/run")
def run_morning_report(session: Session = Depends(session_dependency), settings: Settings = Depends(get_settings)):
    ensure_tables(session)
    try:
        build_morning_report_service(session, settings).run()
    except ValueError as exc:
        session.rollback()
        _record_manual_run_error(session, settings, "skipped", str(exc))
    except Exception as exc:
        session.rollback()
        _record_manual_run_error(session, settings, "failed", str(exc))
    return RedirectResponse("/push-records", status_code=303)


@router.get("/push-records")
def push_records_page(request: Request, session: Session = Depends(session_dependency)):
    ensure_tables(session)
    records = PushRecordRepository(session).list_recent(limit=50)
    return templates.TemplateResponse(request, "push_records.html", {"records": records})


@router.get("/push-records/{push_id}")
def push_record_detail(push_id: str, request: Request, session: Session = Depends(session_dependency)):
    ensure_tables(session)
    records = [record for record in PushRecordRepository(session).list_recent(limit=100) if record.push_id == push_id]
    record = records[0] if records else None
    return templates.TemplateResponse(request, "push_detail.html", {"record": record})


@router.get("/api/status")
def api_status(settings: Settings = Depends(get_settings)):
    return {
        "deepseek_configured": bool(settings.deepseek_api_key),
        "server_chan_configured": bool(settings.server_chan_send_key),
        "deepseek_pro_model": settings.deepseek_pro_model,
        "deepseek_flash_model": settings.deepseek_flash_model,
    }
