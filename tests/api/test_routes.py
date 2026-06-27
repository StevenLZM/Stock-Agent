from fastapi.testclient import TestClient

from stock_agent.app.api import routes
from stock_agent.app.main import app
from stock_agent.app.repositories.push_records import PushRecordRepository


client = TestClient(app)


def test_dashboard_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Stock Agent" in response.text


def test_create_target_from_form():
    response = client.post(
        "/targets",
        data={"symbol": "600519", "name": "贵州茅台", "target_type": "stock"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


def test_status_api_reports_config_state():
    response = client.get("/api/status")
    assert response.status_code == 200
    assert "deepseek_configured" in response.json()


def test_manual_morning_report_trigger_runs_service(monkeypatch):
    calls = []

    class FakeService:
        def __init__(self, session):
            self.session = session

        def run(self):
            calls.append("run")
            return PushRecordRepository(self.session).create(
                push_id="push_test",
                title="测试早报",
                content="测试内容",
                channel="server_chan",
                status="sent",
                evidence_ids=[],
            )

    def fake_build_morning_report_service(session, settings):
        return FakeService(session)

    monkeypatch.setattr(routes, "build_morning_report_service", fake_build_morning_report_service)
    response = client.post("/reports/morning/run", follow_redirects=False)
    assert response.status_code in {302, 303}
    assert response.headers["location"] == "/push-records"
    assert calls == ["run"]
