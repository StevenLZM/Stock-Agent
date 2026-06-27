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


def test_fetch_snapshot_reuses_spot_frames_within_provider_instance():
    calls = {"stock": 0, "index": 0}
    stock_df = pd.DataFrame(
        [
            {"代码": "600519", "名称": "贵州茅台", "最新价": 1500.5, "涨跌幅": 1.2, "成交量": 100, "成交额": 2000.0},
            {"代码": "000001", "名称": "平安银行", "最新价": 12.3, "涨跌幅": -0.5, "成交量": 300, "成交额": 4000.0},
        ]
    )
    index_df = pd.DataFrame(
        [{"代码": "000001", "名称": "上证指数", "最新价": 4027.26, "涨跌幅": -2.26, "成交量": 1000, "成交额": 20000.0}]
    )

    def stock_spot_func():
        calls["stock"] += 1
        return stock_df

    def index_spot_func():
        calls["index"] += 1
        return index_df

    provider = AKShareMarketDataProvider(stock_spot_func=stock_spot_func, index_spot_func=index_spot_func)

    assert provider.fetch_snapshot("600519", "stock").name == "贵州茅台"
    assert provider.fetch_snapshot("000001", "stock").name == "平安银行"
    assert provider.fetch_snapshot("000001", "index").name == "上证指数"
    assert provider.fetch_snapshot("600519", "stock").name == "贵州茅台"

    assert calls == {"stock": 1, "index": 1}


def test_fetch_snapshot_raises_when_symbol_missing():
    provider = AKShareMarketDataProvider(stock_spot_func=lambda: pd.DataFrame([]))
    with pytest.raises(ValueError, match="No market data found"):
        provider.fetch_snapshot("600519", "stock")
