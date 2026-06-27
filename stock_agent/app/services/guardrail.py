from dataclasses import dataclass

from stock_agent.app.domain.schemas import ReportContent


RISKY_TERMS = ("买入", "卖出", "持有", "必涨", "稳赚", " guaranteed ", "buy ", "sell ", "hold ")


@dataclass(frozen=True)
class GuardrailResult:
    passed: bool
    reasons: list[str]


class Guardrail:
    def validate(self, report: ReportContent) -> GuardrailResult:
        reasons: list[str] = []
        text = report.as_markdown()
        lowered = f" {text.lower()} "
        if any(term in text or term in lowered for term in RISKY_TERMS):
            reasons.append("investment_advice")
        if not report.risk_note.strip():
            reasons.append("missing_risk_note")
        return GuardrailResult(passed=not reasons, reasons=reasons)
