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


def test_guardrail_rejects_unsupported_numeric_claims():
    result = Guardrail().validate(make_report("最新价 1500.5，涨跌幅 9.9%"), allowed_numbers={"1500.5"})
    assert result.passed is False
    assert "unsupported_numeric_claim" in result.reasons
