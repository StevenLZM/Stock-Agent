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
