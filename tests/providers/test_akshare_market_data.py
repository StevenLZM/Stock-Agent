import pandas as pd
import pytest

from stock_agent.app.providers.akshare_market_data import AKShareMarketDataProvider


def test_fetch_stock_snapshot_normalizes_akshare_row():
    stock_df = pd.DataFrame(
        [{"代码": "600519", "名称": "贵州茅台", "最新价": 1500.5, "涨跌幅": 1.2, "成交量": 100, "成交额": 2000.0}]
    )
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
