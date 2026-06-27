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
