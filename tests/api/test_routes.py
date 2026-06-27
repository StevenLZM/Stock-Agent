from fastapi.testclient import TestClient

from stock_agent.app.main import app


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
