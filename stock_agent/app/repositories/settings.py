import json
from typing import Any

from sqlalchemy.orm import Session

from stock_agent.app.models.tables import AppSetting


class SettingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def set(self, key: str, value: Any, is_secret: bool = False) -> AppSetting:
        setting = self.session.get(AppSetting, key)
        value_json = json.dumps(value, ensure_ascii=False)
        if setting is None:
            setting = AppSetting(key=key, value_json=value_json, is_secret=is_secret)
            self.session.add(setting)
        else:
            setting.value_json = value_json
            setting.is_secret = is_secret
        self.session.flush()
        return setting

    def get(self, key: str) -> AppSetting | None:
        return self.session.get(AppSetting, key)
