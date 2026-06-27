from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from stock_agent.app.core.config import Settings
from stock_agent.app.core.database import get_session
from stock_agent.app.models.tables import Base
from stock_agent.app.repositories.evidence import EvidenceRepository
from stock_agent.app.repositories.push_records import PushRecordRepository
from stock_agent.app.repositories.settings import SettingsRepository
from stock_agent.app.repositories.watch_targets import WatchTargetRepository


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "web" / "templates"))


def get_settings() -> Settings:
    return Settings()


def ensure_tables(session: Session) -> None:
    Base.metadata.create_all(bind=session.get_bind())


def session_dependency():
    yield from get_session()


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
def run_morning_report():
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
