# Iteration 1 Real Data and DeepSeek Design

Date: 2026-06-27
Status: Approved for implementation planning

## Goal

Build the first usable local loop for the stock and index information push agent:

1. Configure A-share stocks and A-share related indexes in a local Web UI.
2. Fetch real market data through an AKShare-backed provider.
3. Generate a morning report with DeepSeek.
4. Run basic factual and compliance guardrails.
5. Send the concise report through ServerChan Turbo.
6. Store push history and evidence in SQLite.
7. Display configuration, generated reports, evidence, push status, and failures in the Web UI.

This iteration establishes production-shaped boundaries with real external integrations, while keeping the product local, single-user, and testable.

## Explicit Runtime Environment

All development commands for this project run in the `stack-agent` conda environment.

Examples:

```bash
conda run -n stack-agent pytest
conda run -n stack-agent uvicorn stock_agent.app.main:app --reload
```

Interactive shells should use:

```bash
conda activate stack-agent
```

## Product Scope

Included in this iteration:

- FastAPI application skeleton.
- SQLite persistence through Repository interfaces.
- Alembic-managed schema migrations.
- Local Web UI with Jinja templates and HTMX-friendly routes.
- Watch target CRUD for A-share stocks and A-share related indexes.
- App settings for report time, ServerChan Turbo SendKey, DeepSeek model names, and data source behavior.
- AKShare market data provider for current A-share and index snapshots.
- Evidence storage for every market data item used by reports.
- DeepSeek LLM provider with configurable pro and flash model IDs.
- Morning report generation based only on structured evidence.
- Basic Guardrail checks for risky investment-advice wording, missing risk prompt, and unsupported numeric claims.
- ServerChan Turbo push channel with request timeout, failure capture, and redacted logging.
- Push history list and detail views.
- Manual trigger endpoint for morning report generation, used for local validation and first-iteration demos.
- Tests for settings, target validation, repository behavior, report generation flow, guardrail behavior, and push request construction.

Excluded from this iteration:

- Intraday high-frequency alerting.
- Full news, announcement, financial-report, and calendar aggregation.
- Enterprise WeCom webhook delivery implementation beyond configuration placeholder fields.
- Complex P50/P95/P99 latency dashboard.
- Multi-user authentication or cloud deployment.
- Automatic trading or investment recommendations.

## Architecture

The first iteration uses a local monolith with internal boundaries:

```text
Browser
  -> FastAPI Web/API routes
    -> Config Service
    -> Watch Target Service
    -> Report Service
      -> AKShare Market Data Provider
      -> Evidence Repository
      -> DeepSeek LLM Provider
      -> Guardrail
      -> Push Service
      -> Push Record Repository
    -> SQLite
```

Business services call repositories and providers through typed interfaces. FastAPI routes do not directly query SQLite or call external APIs. This keeps the first version simple while preserving later replacement points for MySQL, alternate data sources, and alternate LLM providers.

## Data Source Design

`MarketDataProvider` defines the market data boundary. The first concrete provider is `AKShareMarketDataProvider`.

The provider returns normalized snapshot objects with:

- `symbol`
- `name`
- `market`
- `target_type`
- `last_price`
- `change_percent`
- `volume`
- `amount`
- `data_timestamp`
- `source`
- `source_url`
- `raw_payload`

The report service stores each snapshot as an `EvidenceItem` before sending it to DeepSeek. If AKShare fails or required fields are missing, the system records a job/report failure and does not ask the LLM to invent missing information.

## DeepSeek Design

DeepSeek is accessed through an `LLMProvider` interface and a `DeepSeekLLMProvider` implementation.

Secret values and immutable defaults are read from environment variables. User-editable model names can be stored in `app_settings` and fall back to the environment defaults:

```text
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_PRO_MODEL=deepseek-v4-pro
DEEPSEEK_FLASH_MODEL=deepseek-v4-flash
```

Model usage:

- `deepseek-v4-pro`: default for morning reports and later closing reviews where quality matters more.
- `deepseek-v4-flash`: default for low-latency summaries, test generation paths, and future intraday alerting.

The API key must never be committed. The repository includes `.env.example` with empty placeholders only. Logs redact key-like values.

The prompt contract requires DeepSeek to produce structured output with:

- `title`
- `summary`
- `key_points`
- `evidence_refs`
- `watch_items`
- `risk_note`

The prompt states that the model may only use supplied evidence and must not provide buy, sell, hold, guaranteed return, or deterministic price-movement claims.

## Guardrail Design

The first guardrail implementation is intentionally small and deterministic:

- Reject or downgrade text containing direct investment instructions such as buy, sell, hold, must rise, guaranteed profit, or equivalent Chinese phrases.
- Require a risk note.
- Require every numeric claim involving prices, percentages, or time to match an evidence value or timestamp supplied to the report service.
- If the LLM output fails guardrail checks, use a structured factual fallback summary built from evidence snapshots.

The first version does not attempt semantic fact-checking beyond evidence-field matching.

## Persistence Design

SQLite is the default storage engine. The app reads `DATABASE_URL`, defaulting to `sqlite:///stock_agent.db`.

Core tables:

- `watch_targets`
- `app_settings`
- `evidence_items`
- `push_records`

The first iteration may include a minimal `jobs` table if the manual report trigger is implemented through the same job boundary. If not, job persistence is deferred to iteration 2.

Repository interfaces:

- `WatchTargetRepository`
- `SettingsRepository`
- `EvidenceRepository`
- `PushRecordRepository`

All JSON fields are serialized in application code as text. Business services do not use SQLite-specific SQL.

## Web UI Design

The first UI is utilitarian and focused:

- Dashboard showing configured targets, latest report status, latest push records, and missing configuration warnings.
- Watch target management page.
- Settings page for ServerChan SendKey and DeepSeek model names.
- Manual morning report trigger.
- Push history page.
- Push detail page showing content, status, evidence IDs, error message, and timestamps.

Jinja templates render server-side HTML. HTMX attributes can be used for incremental interactions, but the first iteration must work without a frontend build pipeline.

## API Design

Initial endpoints:

```text
GET    /
GET    /targets
POST   /targets
POST   /targets/{id}/delete
GET    /settings
POST   /settings
POST   /channels/server-chan/test
POST   /reports/morning/run
GET    /push-records
GET    /push-records/{push_id}
GET    /api/status
```

JSON API endpoints may be added where tests or HTMX interactions benefit, but the first iteration prioritizes a working local Web flow.

## Error Handling

- Missing DeepSeek API key: report generation stops with a visible configuration error.
- Missing ServerChan SendKey: report can be generated and stored, but push is skipped with a clear status.
- AKShare failure: report generation fails before LLM invocation, and the error is displayed in push/history or status views.
- DeepSeek timeout or API failure: fallback factual summary is generated from evidence and recorded as degraded.
- Guardrail failure: fallback factual summary is sent or stored instead of unsafe LLM text.
- Push failure: error message is stored with a redacted request context.

## Testing Strategy

Development follows TDD. Production behavior is implemented only after a failing test has been observed.

Required test coverage:

- Symbol and target-type validation.
- Repository CRUD behavior using a temporary SQLite database.
- Settings redaction and missing-key behavior.
- AKShare provider normalization through a fake dataframe or patched provider call.
- DeepSeek provider request construction without logging secrets.
- Report service flow from targets to evidence to LLM to guardrail to push record.
- Guardrail rejection of investment-advice wording and unsupported numeric claims.
- ServerChan request construction and failure recording.
- FastAPI route smoke tests for dashboard, target CRUD, settings save, manual report trigger, and push history.

External network calls are not made in unit tests. Provider and HTTP clients accept injectable callables or clients so tests can use deterministic fakes.

## Security and Secrets

- `.env` is gitignored.
- `.env.example` contains placeholder keys only.
- API keys and SendKeys are redacted in logs and UI status messages.
- The user-supplied DeepSeek key is treated as already sensitive and is not written into repository files.

## Implementation Notes

- Use `conda run -n stack-agent ...` for test and app commands.
- Prefer focused files under `stock_agent/app/`.
- Keep iteration 1 small enough to verify locally end to end.
- Do not introduce React/Vite or a background worker unless the first iteration cannot pass without it.
- Keep AKShare behind a provider interface because public data-source behavior may drift.
