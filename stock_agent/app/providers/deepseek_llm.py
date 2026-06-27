import json
from typing import Literal

import httpx

from stock_agent.app.domain.schemas import MarketSnapshot, ReportContent


PROMPT_RULE = (
    "只使用输入的结构化证据生成摘要。禁止给出买入、卖出、持有、必涨、稳赚或确定性收益判断。"
    "输出 JSON，字段为 title, summary, key_points, evidence_refs, watch_items, risk_note。"
)


class DeepSeekLLMProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        pro_model: str = "deepseek-v4-pro",
        flash_model: str = "deepseek-v4-flash",
        client: httpx.Client | None = None,
    ):
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.pro_model = pro_model
        self.flash_model = flash_model
        self.client = client or httpx.Client(timeout=30)

    def generate_morning_report(
        self,
        evidence: list[MarketSnapshot],
        quality: Literal["pro", "flash"] = "pro",
    ) -> ReportContent:
        model = self.pro_model if quality == "pro" else self.flash_model
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": PROMPT_RULE},
                    {"role": "user", "content": json.dumps([item.model_dump(mode="json") for item in evidence], ensure_ascii=False)},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("DeepSeek response must be valid JSON") from exc
        return ReportContent.model_validate(payload)
