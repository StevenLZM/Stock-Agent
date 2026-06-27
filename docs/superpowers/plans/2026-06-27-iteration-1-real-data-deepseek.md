# Iteration 1 Real Data and DeepSeek Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first local, single-user stock agent loop with real AKShare market data, DeepSeek summaries, ServerChan Turbo delivery, SQLite history, and a server-rendered Web UI.

**Architecture:** The app is a FastAPI monolith with internal service, provider, repository, and template boundaries. External systems are behind interfaces: AKShare for market data, DeepSeek for LLM summaries, and ServerChan for push delivery. SQLite is accessed through repositories so later MySQL migration does not rewrite business services.

**Tech Stack:** Python, FastAPI, Jinja2, SQLAlchemy, Alembic, Pydantic Settings, httpx, AKShare, pandas, pytest, SQLite, conda environment `stack-agent`.

---

## File Structure

Create this structure:

```text
pyproject.toml
.gitignore
.env.example
README.md
alembic.ini
migrations/
  env.py
  versions/0001_initial.py
stock_agent/
  __init__.py
  app/
    __init__.py
    main.py
    api/
      __init__.py
      routes.py
    core/
      __init__.py
      config.py
      database.py
      redaction.py
    domain/
      __init__.py
      schemas.py
    models/
      __init__.py
      tables.py
    repositories/
      __init__.py
      evidence.py
      push_records.py
      settings.py
      watch_targets.py
    services/
      __init__.py
      guardrail.py
      reports.py
    providers/
      __init__.py
      akshare_market_data.py
      deepseek_llm.py
      server_chan.py
    web/
      __init__.py
      templates/
        base.html
        dashboard.html
        push_detail.html
        push_records.html
        settings.html
        targets.html
tests/
  conftest.py
  api/test_routes.py
  core/test_config.py
  domain/test_schemas.py
  providers/test_akshare_market_data.py
  providers/test_deepseek_llm.py
  providers/test_server_chan.py
  repositories/test_repositories.py
  services/test_guardrail.py
  services/test_reports.py
```

Responsibilities:

- `core/`: settings, database engine/session creation, redaction utilities.
- `domain/`: Pydantic/domain objects used by services and providers.
- `models/`: SQLAlchemy table models only.
- `repositories/`: database access and transaction-free CRUD methods.
- `providers/`: external system adapters and request/response normalization.
- `services/`: business workflows and validation.
- `api/routes.py`: Web routes and dependency wiring.
- `web/templates/`: server-rendered UI.

## Shared Commands

Use these commands throughout:

```bash
conda run -n stack-agent python -m pip install -e ".[dev]"
conda run -n stack-agent pytest
conda run -n stack-agent pytest tests/path/to/test_file.py -v
conda run -n stack-agent uvicorn stock_agent.app.main:app --reload
```

Do not put real secrets in repository files. Use a local `.env` with:

```text
DEEPSEEK_API_KEY=<real key kept local>
SERVER_CHAN_SEND_KEY=<real key kept local>
```

## Task 1: Project Scaffold and Runtime Config

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `stock_agent/__init__.py`
- Create: `stock_agent/app/__init__.py`
- Create: `stock_agent/app/core/__init__.py`
- Create: `stock_agent/app/core/config.py`
- Create: `stock_agent/app/core/redaction.py`
- Create: `tests/conftest.py`
- Create: `tests/core/test_config.py`

- [ ] **Step 1: Write the failing config and redaction tests**

Create `tests/core/test_config.py`:

```python
from stock_agent.app.core.config import Settings
from stock_agent.app.core.redaction import redact_secret


def test_settings_use_deepseek_v4_defaults(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    settings = Settings()
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_pro_model == "deepseek-v4-pro"
    assert settings.deepseek_flash_model == "deepseek-v4-flash"
    assert settings.database_url == "sqlite:///stock_agent.db"


def test_redact_secret_keeps_edges_only():
    assert redact_secret("sk-1234567890abcdef") == "sk-1***********cdef"
    assert redact_secret("") == ""
    assert redact_secret(None) == ""
```

- [ ] **Step 2: Verify the tests fail for missing modules**

Run:

```bash
conda run -n stack-agent pytest tests/core/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'stock_agent'`.

- [ ] **Step 3: Add packaging and dependency metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "stock-agent"
version = "0.1.0"
description = "Local A-share stock and index information push agent"
requires-python = ">=3.11"
dependencies = [
  "akshare>=1.15.0",
  "alembic>=1.13.0",
  "fastapi>=0.115.0",
  "httpx>=0.27.0",
  "jinja2>=3.1.0",
  "pandas>=2.2.0",
  "pydantic>=2.8.0",
  "pydantic-settings>=2.4.0",
  "python-dotenv>=1.0.0",
  "python-multipart>=0.0.9",
  "sqlalchemy>=2.0.0",
  "uvicorn[standard]>=0.30.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `.gitignore`:

```gitignore
.env
.pytest_cache/
__pycache__/
*.py[cod]
stock_agent.db
*.sqlite
*.sqlite3
.DS_Store
```

Create `.env.example`:

```text
DATABASE_URL=sqlite:///stock_agent.db
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_PRO_MODEL=deepseek-v4-pro
DEEPSEEK_FLASH_MODEL=deepseek-v4-flash
SERVER_CHAN_SEND_KEY=
```

- [ ] **Step 4: Add minimal config and redaction implementation**

Create package marker files as empty files:

```text
stock_agent/__init__.py
stock_agent/app/__init__.py
stock_agent/app/core/__init__.py
```

Create `stock_agent/app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///stock_agent.db"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_pro_model: str = "deepseek-v4-pro"
    deepseek_flash_model: str = "deepseek-v4-flash"
    server_chan_send_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

Create `stock_agent/app/core/redaction.py`:

```python
def redact_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
```

Create `tests/conftest.py`:

```python
import os


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
```

- [ ] **Step 5: Install dependencies and verify green**

Run:

```bash
conda run -n stack-agent python -m pip install -e ".[dev]"
conda run -n stack-agent pytest tests/core/test_config.py -v
```

Expected: PASS, 2 tests.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore .env.example stock_agent tests
git commit -m "chore: scaffold stock agent project"
```

## Task 2: Domain Schemas and Target Validation

**Files:**
- Create: `stock_agent/app/domain/__init__.py`
- Create: `stock_agent/app/domain/schemas.py`
- Create: `tests/domain/test_schemas.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/domain/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from stock_agent.app.domain.schemas import MarketSnapshot, TargetCreate


def test_target_create_accepts_a_share_stock_symbol():
    target = TargetCreate(symbol="600519", name="贵州茅台", target_type="stock")
    assert target.symbol == "600519"
    assert target.market == "CN"
    assert target.enabled is True


def test_target_create_accepts_cn_index_symbol():
    target = TargetCreate(symbol="000300", name="沪深300", target_type="index")
    assert target.target_type == "index"


def test_target_create_rejects_non_six_digit_symbol():
    with pytest.raises(ValidationError):
        TargetCreate(symbol="AAPL", name="Apple", target_type="stock")


def test_market_snapshot_requires_source_and_price():
    snapshot = MarketSnapshot(
        symbol="600519",
        name="贵州茅台",
        market="CN",
        target_type="stock",
        last_price=1500.5,
        change_percent=1.2,
        volume=123456,
        amount=987654321.0,
        data_timestamp="2026-06-27T09:30:00+08:00",
        source="akshare",
        source_url="https://akshare.akfamily.xyz/",
        raw_payload={"代码": "600519"},
    )
    assert snapshot.last_price == 1500.5
```

- [ ] **Step 2: Verify red**

Run:

```bash
conda run -n stack-agent pytest tests/domain/test_schemas.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `schemas`.

- [ ] **Step 3: Implement domain schemas**

Create `stock_agent/app/domain/__init__.py` as an empty file.

Create `stock_agent/app/domain/schemas.py`:

```python
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


TargetType = Literal["stock", "index"]
PushStatus = Literal["sent", "skipped", "failed", "degraded"]


class TargetCreate(BaseModel):
    symbol: str
    name: str
    target_type: TargetType
    market: str = "CN"
    enabled: bool = True
    cooldown_minutes: int = Field(default=60, ge=0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) != 6 or not normalized.isdigit():
            raise ValueError("symbol must be a six-digit A-share or index code")
        return normalized

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name is required")
        return normalized


class TargetRead(TargetCreate):
    id: int


class MarketSnapshot(BaseModel):
    symbol: str
    name: str
    market: str
    target_type: TargetType
    last_price: float
    change_percent: float
    volume: float
    amount: float
    data_timestamp: datetime | str
    source: str
    source_url: str
    raw_payload: dict[str, Any]


class ReportContent(BaseModel):
    title: str
    summary: str
    key_points: list[str]
    evidence_refs: list[str]
    watch_items: list[str]
    risk_note: str

    def as_markdown(self) -> str:
        sections = [
            f"# {self.title}",
            self.summary,
            "## 关键点",
            *[f"- {point}" for point in self.key_points],
            "## 后续观察",
            *[f"- {item}" for item in self.watch_items],
            f"## 风险提示\n{self.risk_note}",
        ]
        return "\n\n".join(sections)
```

- [ ] **Step 4: Verify green**

Run:

```bash
conda run -n stack-agent pytest tests/domain/test_schemas.py -v
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add stock_agent/app/domain tests/domain/test_schemas.py
git commit -m "feat: add domain schemas"
```

## Task 3: Database Models, Alembic, and Repositories

**Files:**
- Create: `stock_agent/app/core/database.py`
- Create: `stock_agent/app/models/__init__.py`
- Create: `stock_agent/app/models/tables.py`
- Create: `stock_agent/app/repositories/__init__.py`
- Create: `stock_agent/app/repositories/watch_targets.py`
- Create: `stock_agent/app/repositories/settings.py`
- Create: `stock_agent/app/repositories/evidence.py`
- Create: `stock_agent/app/repositories/push_records.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_initial.py`
- Create: `tests/repositories/test_repositories.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/repositories/test_repositories.py`:

```python
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
```

- [ ] **Step 2: Verify red**

Run:

```bash
conda run -n stack-agent pytest tests/repositories/test_repositories.py -v
```

Expected: FAIL because `stock_agent.app.models` and repositories do not exist.

- [ ] **Step 3: Implement database setup, models, and repositories**

Create `stock_agent/app/core/database.py` with `create_engine`, `sessionmaker`, and `get_session`.

Create `stock_agent/app/models/tables.py` with SQLAlchemy declarative `Base` and these models:

```python
WatchTarget(id, symbol, name, market, target_type, enabled, cooldown_minutes, created_at, updated_at)
AppSetting(key, value_json, is_secret, updated_at)
EvidenceItem(id, symbol, target_type, evidence_type, source, source_url, data_timestamp, collected_at, payload_json, created_at)
PushRecord(id, push_id, title, content, channel, status, evidence_ids_json, error_message, created_at, sent_at)
```

Implement repository methods used by the test. Serialize JSON with `json.dumps(value, ensure_ascii=False)` and deserialize with `json.loads(stored_value)`.

- [ ] **Step 4: Add Alembic files**

Create `alembic.ini` pointing at `migrations`, and create `migrations/env.py` importing `Base.metadata`. Create `migrations/versions/0001_initial.py` with `upgrade()` creating the four tables and `downgrade()` dropping them in reverse order.

- [ ] **Step 5: Verify green**

Run:

```bash
conda run -n stack-agent pytest tests/repositories/test_repositories.py -v
```

Expected: PASS, 3 tests.

- [ ] **Step 6: Commit**

```bash
git add stock_agent/app/core/database.py stock_agent/app/models stock_agent/app/repositories alembic.ini migrations tests/repositories/test_repositories.py
git commit -m "feat: add sqlite repositories"
```

## Task 4: AKShare Market Data Provider

**Files:**
- Create: `stock_agent/app/providers/__init__.py`
- Create: `stock_agent/app/providers/akshare_market_data.py`
- Create: `tests/providers/test_akshare_market_data.py`

- [ ] **Step 1: Write failing provider normalization tests**

Create `tests/providers/test_akshare_market_data.py`:

```python
import pandas as pd
import pytest

from stock_agent.app.providers.akshare_market_data import AKShareMarketDataProvider


def test_fetch_stock_snapshot_normalizes_akshare_row():
    stock_df = pd.DataFrame([
        {"代码": "600519", "名称": "贵州茅台", "最新价": 1500.5, "涨跌幅": 1.2, "成交量": 100, "成交额": 2000.0}
    ])
    provider = AKShareMarketDataProvider(stock_spot_func=lambda: stock_df)
    snapshot = provider.fetch_snapshot("600519", "stock")
    assert snapshot.symbol == "600519"
    assert snapshot.name == "贵州茅台"
    assert snapshot.last_price == 1500.5
    assert snapshot.source == "akshare"


def test_fetch_snapshot_raises_when_symbol_missing():
    provider = AKShareMarketDataProvider(stock_spot_func=lambda: pd.DataFrame([]))
    with pytest.raises(ValueError, match="No market data found"):
        provider.fetch_snapshot("600519", "stock")
```

- [ ] **Step 2: Verify red**

Run:

```bash
conda run -n stack-agent pytest tests/providers/test_akshare_market_data.py -v
```

Expected: FAIL because provider module does not exist.

- [ ] **Step 3: Implement provider with injectable AKShare functions**

Create `stock_agent/app/providers/akshare_market_data.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd

from stock_agent.app.domain.schemas import MarketSnapshot, TargetType


AKSHARE_DOC_URL = "https://akshare.akfamily.xyz/"


class AKShareMarketDataProvider:
    def __init__(self, stock_spot_func=None, index_spot_func=None):
        self._stock_spot_func = stock_spot_func or ak.stock_zh_a_spot_em
        self._index_spot_func = index_spot_func or ak.stock_zh_index_spot_em

    def fetch_snapshot(self, symbol: str, target_type: TargetType) -> MarketSnapshot:
        frame = self._stock_spot_func() if target_type == "stock" else self._index_spot_func()
        row = self._find_row(frame, symbol)
        return MarketSnapshot(
            symbol=str(row["代码"]).zfill(6),
            name=str(row["名称"]),
            market="CN",
            target_type=target_type,
            last_price=float(row["最新价"]),
            change_percent=float(row["涨跌幅"]),
            volume=float(row.get("成交量", 0) or 0),
            amount=float(row.get("成交额", 0) or 0),
            data_timestamp=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            source="akshare",
            source_url=AKSHARE_DOC_URL,
            raw_payload=row.to_dict(),
        )

    def _find_row(self, frame: pd.DataFrame, symbol: str) -> pd.Series:
        if frame.empty or "代码" not in frame.columns:
            raise ValueError(f"No market data found for {symbol}")
        normalized = frame.copy()
        normalized["代码"] = normalized["代码"].astype(str).str.zfill(6)
        matches = normalized[normalized["代码"] == symbol]
        if matches.empty:
            raise ValueError(f"No market data found for {symbol}")
        return matches.iloc[0]
```

- [ ] **Step 4: Verify green**

Run:

```bash
conda run -n stack-agent pytest tests/providers/test_akshare_market_data.py -v
```

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add stock_agent/app/providers tests/providers/test_akshare_market_data.py
git commit -m "feat: add akshare market data provider"
```

## Task 5: Guardrail Service

**Files:**
- Create: `stock_agent/app/services/__init__.py`
- Create: `stock_agent/app/services/guardrail.py`
- Create: `tests/services/test_guardrail.py`

- [ ] **Step 1: Write failing guardrail tests**

Create `tests/services/test_guardrail.py`:

```python
from stock_agent.app.domain.schemas import ReportContent
from stock_agent.app.services.guardrail import Guardrail


def make_report(summary: str, risk_note: str = "以上仅为信息整理，不构成投资建议。") -> ReportContent:
    return ReportContent(
        title="早报",
        summary=summary,
        key_points=["贵州茅台 最新价 1500.5"],
        evidence_refs=["600519"],
        watch_items=["观察成交量变化"],
        risk_note=risk_note,
    )


def test_guardrail_rejects_direct_investment_instruction():
    result = Guardrail().validate(make_report("建议买入贵州茅台"))
    assert result.passed is False
    assert "investment_advice" in result.reasons


def test_guardrail_requires_risk_note():
    result = Guardrail().validate(make_report("今日涨跌幅 1.2%", risk_note=""))
    assert result.passed is False
    assert "missing_risk_note" in result.reasons


def test_guardrail_accepts_evidence_backed_numbers():
    result = Guardrail().validate(make_report("最新价 1500.5，涨跌幅 1.2%"), allowed_numbers={"1500.5", "1.2"})
    assert result.passed is True
```

- [ ] **Step 2: Verify red**

Run:

```bash
conda run -n stack-agent pytest tests/services/test_guardrail.py -v
```

Expected: FAIL because `Guardrail` does not exist.

- [ ] **Step 3: Implement deterministic guardrail**

Create `stock_agent/app/services/__init__.py` as an empty file.

Create `stock_agent/app/services/guardrail.py`:

```python
import re
from dataclasses import dataclass

from stock_agent.app.domain.schemas import ReportContent


RISKY_TERMS = ("买入", "卖出", "持有", "必涨", "稳赚", " guaranteed ", "buy ", "sell ", "hold ")
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?%?")


@dataclass(frozen=True)
class GuardrailResult:
    passed: bool
    reasons: list[str]


class Guardrail:
    def validate(self, report: ReportContent, allowed_numbers: set[str] | None = None) -> GuardrailResult:
        reasons: list[str] = []
        text = report.as_markdown()
        lowered = f" {text.lower()} "
        if any(term in text or term in lowered for term in RISKY_TERMS):
            reasons.append("investment_advice")
        if not report.risk_note.strip():
            reasons.append("missing_risk_note")
        allowed = allowed_numbers or set()
        unsupported = [
            match.group(0).rstrip("%")
            for match in NUMBER_RE.finditer(text)
            if match.group(0).rstrip("%") not in allowed
        ]
        if allowed_numbers is not None and unsupported:
            reasons.append("unsupported_numeric_claim")
        return GuardrailResult(passed=not reasons, reasons=reasons)
```

- [ ] **Step 4: Verify green**

Run:

```bash
conda run -n stack-agent pytest tests/services/test_guardrail.py -v
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add stock_agent/app/services tests/services/test_guardrail.py
git commit -m "feat: add report guardrail"
```

## Task 6: DeepSeek LLM Provider

**Files:**
- Create: `stock_agent/app/providers/deepseek_llm.py`
- Create: `tests/providers/test_deepseek_llm.py`

- [ ] **Step 1: Write failing DeepSeek provider tests**

Create `tests/providers/test_deepseek_llm.py`:

```python
import httpx
import pytest

from stock_agent.app.domain.schemas import MarketSnapshot
from stock_agent.app.providers.deepseek_llm import DeepSeekLLMProvider


def test_deepseek_provider_sends_flash_or_pro_model():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "{\"title\":\"早报\",\"summary\":\"摘要\",\"key_points\":[\"点\"],\"evidence_refs\":[\"600519\"],\"watch_items\":[\"观察\"],\"risk_note\":\"仅为信息整理，不构成投资建议。\"}"}}]
        })

    provider = DeepSeekLLMProvider(
        api_key="sk-test",
        base_url="https://api.deepseek.com",
        pro_model="deepseek-v4-pro",
        flash_model="deepseek-v4-flash",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    report = provider.generate_morning_report([], quality="pro")
    assert report.title == "早报"
    assert b"deepseek-v4-pro" in requests[0].content
    assert requests[0].headers["Authorization"] == "Bearer sk-test"


def test_deepseek_provider_requires_api_key():
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekLLMProvider(api_key="")
```

- [ ] **Step 2: Verify red**

Run:

```bash
conda run -n stack-agent pytest tests/providers/test_deepseek_llm.py -v
```

Expected: FAIL because `DeepSeekLLMProvider` does not exist.

- [ ] **Step 3: Implement DeepSeek request construction and parsing**

Create `stock_agent/app/providers/deepseek_llm.py` with:

- constructor requiring API key;
- `generate_morning_report(evidence: list[MarketSnapshot], quality: Literal["pro", "flash"])`;
- OpenAI-compatible `POST /chat/completions`;
- JSON content parsing into `ReportContent`;
- 30 second timeout.

Use this prompt rule in the user message:

```text
只使用输入的结构化证据生成摘要。禁止给出买入、卖出、持有、必涨、稳赚或确定性收益判断。输出 JSON，字段为 title, summary, key_points, evidence_refs, watch_items, risk_note。
```

- [ ] **Step 4: Verify green**

Run:

```bash
conda run -n stack-agent pytest tests/providers/test_deepseek_llm.py -v
```

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add stock_agent/app/providers/deepseek_llm.py tests/providers/test_deepseek_llm.py
git commit -m "feat: add deepseek llm provider"
```

## Task 7: ServerChan Turbo Provider

**Files:**
- Create: `stock_agent/app/providers/server_chan.py`
- Create: `tests/providers/test_server_chan.py`

- [ ] **Step 1: Write failing ServerChan tests**

Create `tests/providers/test_server_chan.py`:

```python
import httpx
import pytest

from stock_agent.app.providers.server_chan import ServerChanProvider


def test_server_chan_posts_title_and_markdown_content():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": 0, "message": "success"})

    provider = ServerChanProvider(send_key="SCT123", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = provider.send(title="早报", content="# 早报")
    assert result.success is True
    assert str(requests[0].url) == "https://sctapi.ftqq.com/SCT123.send"
    assert b"title=" in requests[0].content


def test_server_chan_requires_send_key():
    with pytest.raises(ValueError, match="SERVER_CHAN_SEND_KEY"):
        ServerChanProvider(send_key="")
```

- [ ] **Step 2: Verify red**

Run:

```bash
conda run -n stack-agent pytest tests/providers/test_server_chan.py -v
```

Expected: FAIL because `ServerChanProvider` does not exist.

- [ ] **Step 3: Implement provider**

Create `stock_agent/app/providers/server_chan.py` with:

- constructor requiring `send_key`;
- `send(title: str, content: str) -> PushSendResult`;
- POST to `https://sctapi.ftqq.com/{send_key}.send`;
- form fields `title`, `desp`;
- success when HTTP status is 2xx and response JSON has `code` equal to `0`;
- failure result with `error_message` for non-2xx or nonzero code.

- [ ] **Step 4: Verify green**

Run:

```bash
conda run -n stack-agent pytest tests/providers/test_server_chan.py -v
```

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add stock_agent/app/providers/server_chan.py tests/providers/test_server_chan.py
git commit -m "feat: add serverchan push provider"
```

## Task 8: Morning Report Service

**Files:**
- Create: `stock_agent/app/services/reports.py`
- Create: `tests/services/test_reports.py`

- [ ] **Step 1: Write failing report service tests**

Create `tests/services/test_reports.py`:

```python
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
    service = MorningReportService(
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
```

- [ ] **Step 2: Verify red**

Run:

```bash
conda run -n stack-agent pytest tests/services/test_reports.py -v
```

Expected: FAIL because `MorningReportService` does not exist.

- [ ] **Step 3: Implement report orchestration**

Create `stock_agent/app/services/reports.py` with:

- `MorningReportService.__init__` accepting repositories and providers;
- `run()` loading enabled targets;
- fetching snapshots;
- creating evidence rows;
- calling DeepSeek with `quality="pro"`;
- validating with `Guardrail` using allowed numbers from snapshots;
- building factual fallback if guardrail fails or LLM raises;
- calling push provider if configured;
- creating one push record with status `sent`, `failed`, `skipped`, or `degraded`.

- [ ] **Step 4: Verify green**

Run:

```bash
conda run -n stack-agent pytest tests/services/test_reports.py -v
```

Expected: PASS, 1 test.

- [ ] **Step 5: Commit**

```bash
git add stock_agent/app/services/reports.py tests/services/test_reports.py
git commit -m "feat: add morning report service"
```

## Task 9: FastAPI Routes and Web UI

**Files:**
- Create: `stock_agent/app/main.py`
- Create: `stock_agent/app/api/__init__.py`
- Create: `stock_agent/app/api/routes.py`
- Create: `stock_agent/app/web/__init__.py`
- Create: `stock_agent/app/web/templates/base.html`
- Create: `stock_agent/app/web/templates/dashboard.html`
- Create: `stock_agent/app/web/templates/targets.html`
- Create: `stock_agent/app/web/templates/settings.html`
- Create: `stock_agent/app/web/templates/push_records.html`
- Create: `stock_agent/app/web/templates/push_detail.html`
- Create: `tests/api/test_routes.py`

- [ ] **Step 1: Write failing route smoke tests**

Create `tests/api/test_routes.py`:

```python
from fastapi.testclient import TestClient

from stock_agent.app.main import app


client = TestClient(app)


def test_dashboard_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Stock Agent" in response.text


def test_create_target_from_form():
    response = client.post("/targets", data={"symbol": "600519", "name": "贵州茅台", "target_type": "stock"}, follow_redirects=False)
    assert response.status_code in {302, 303}


def test_status_api_reports_config_state():
    response = client.get("/api/status")
    assert response.status_code == 200
    assert "deepseek_configured" in response.json()
```

- [ ] **Step 2: Verify red**

Run:

```bash
conda run -n stack-agent pytest tests/api/test_routes.py -v
```

Expected: FAIL because `stock_agent.app.main` does not exist.

- [ ] **Step 3: Implement FastAPI app and templates**

Create `stock_agent/app/main.py` with `FastAPI()` and include routes.

Create `stock_agent/app/api/routes.py` with:

- database startup creating tables for local dev;
- dependencies for settings and sessions;
- `GET /`;
- target list/create/delete;
- settings page/save;
- ServerChan test send;
- manual morning report trigger;
- push history/detail;
- `GET /api/status`.

Create templates with compact forms and tables. The base template title must contain `Stock Agent` so the smoke test is meaningful.

- [ ] **Step 4: Verify green**

Run:

```bash
conda run -n stack-agent pytest tests/api/test_routes.py -v
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add stock_agent/app/main.py stock_agent/app/api stock_agent/app/web tests/api/test_routes.py
git commit -m "feat: add local web interface"
```

## Task 10: Local Run Documentation and Full Verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write failing documentation check**

Run:

```bash
test -f README.md
```

Expected: FAIL because `README.md` does not exist.

- [ ] **Step 2: Add README with exact commands**

Create `README.md`:

````markdown
# Stock Agent

Local single-user A-share stock and index information push agent.

## Environment

All development commands run in the `stack-agent` conda environment.

```bash
conda activate stack-agent
```

Non-interactive commands:

```bash
conda run -n stack-agent python -m pip install -e ".[dev]"
conda run -n stack-agent pytest
```

## Local Secrets

Create `.env` from `.env.example` and fill local secrets:

```text
DEEPSEEK_API_KEY=
SERVER_CHAN_SEND_KEY=
```

Do not commit `.env`.

## Run

```bash
conda run -n stack-agent uvicorn stock_agent.app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## First Iteration Flow

1. Add at least one A-share stock or A-share related index target.
2. Save DeepSeek model names or use defaults.
3. Save ServerChan Turbo SendKey.
4. Run the morning report manually.
5. Check push history and evidence-backed report content.
````

- [ ] **Step 3: Run full test suite**

Run:

```bash
conda run -n stack-agent pytest
```

Expected: all tests pass.

- [ ] **Step 4: Run import smoke**

Run:

```bash
conda run -n stack-agent python -c "from stock_agent.app.main import app; print(app.title)"
```

Expected output includes:

```text
Stock Agent
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add local run instructions"
```

## Final Verification

Run:

```bash
git status --short
conda run -n stack-agent pytest
conda run -n stack-agent python -c "from stock_agent.app.main import app; print(app.title)"
```

Expected:

- `git status --short` shows a clean tree after final commit.
- `pytest` passes.
- import smoke prints `Stock Agent`.

Manual local app check:

```bash
conda run -n stack-agent uvicorn stock_agent.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`, add target `600519` / `贵州茅台` / `stock`, configure local `.env`, run morning report, and confirm a push record appears.

## Self-Review

Spec coverage:

- FastAPI skeleton: Task 9.
- SQLite repositories and Alembic: Task 3.
- Web UI: Task 9.
- Watch target CRUD: Tasks 2, 3, 9.
- Settings and secrets: Tasks 1, 3, 9, 10.
- AKShare provider: Task 4.
- DeepSeek provider with `deepseek-v4-pro` and `deepseek-v4-flash`: Tasks 1 and 6.
- Guardrail: Task 5.
- ServerChan push: Task 7.
- Morning report flow: Task 8.
- Tests and verification: all tasks plus Final Verification.

No implementation task requires real network access in unit tests. Real network access is limited to manual app validation with local `.env` credentials.
