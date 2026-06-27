from stock_agent.app.core.config import Settings
from stock_agent.app.core.redaction import redact_secret


def test_settings_use_deepseek_v4_defaults(monkeypatch):
    for env_var in (
        "DATABASE_URL",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_PRO_MODEL",
        "DEEPSEEK_FLASH_MODEL",
        "SERVER_CHAN_SEND_KEY",
    ):
        monkeypatch.delenv(env_var, raising=False)

    settings = Settings(_env_file=None)
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_pro_model == "deepseek-v4-pro"
    assert settings.deepseek_flash_model == "deepseek-v4-flash"
    assert settings.database_url == "sqlite:///stock_agent.db"


def test_redact_secret_keeps_edges_only():
    assert redact_secret("sk-1234567890abcdef") == "sk-1***********cdef"
    assert redact_secret("abc") == "***"
    assert redact_secret("") == ""
    assert redact_secret(None) == ""
