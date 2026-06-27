from stock_agent.app.core.config import Settings
from stock_agent.app.core.redaction import redact_secret


SETTINGS_ENV_VARS = (
    "DATABASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_PRO_MODEL",
    "DEEPSEEK_FLASH_MODEL",
    "SERVER_CHAN_SEND_KEY",
)


def clear_settings_env(monkeypatch):
    for env_var in SETTINGS_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


def test_settings_use_deepseek_v4_defaults(monkeypatch):
    clear_settings_env(monkeypatch)

    settings = Settings(_env_file=None)
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_pro_model == "deepseek-v4-pro"
    assert settings.deepseek_flash_model == "deepseek-v4-flash"
    assert settings.database_url == "sqlite:///stock_agent.db"


def test_settings_read_custom_models_from_env_file(monkeypatch, tmp_path):
    clear_settings_env(monkeypatch)
    tmp_env = tmp_path / ".env"
    tmp_env.write_text(
        "\n".join(
            [
                "DEEPSEEK_PRO_MODEL=custom-pro",
                "DEEPSEEK_FLASH_MODEL=custom-flash",
                "UNKNOWN_SETTING=ignored",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=tmp_env)

    assert settings.deepseek_pro_model == "custom-pro"
    assert settings.deepseek_flash_model == "custom-flash"
    assert settings.model_extra is None


def test_redact_secret_keeps_edges_only():
    assert redact_secret("sk-1234567890abcdef") == "sk-1***********cdef"
    assert redact_secret("abc") == "***"
    assert redact_secret("") == ""
    assert redact_secret(None) == ""
