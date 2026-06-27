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
