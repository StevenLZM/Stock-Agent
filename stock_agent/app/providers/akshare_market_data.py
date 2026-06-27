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
        self._spot_frames: dict[TargetType, pd.DataFrame] = {}

    def fetch_snapshot(self, symbol: str, target_type: TargetType) -> MarketSnapshot:
        frame = self._spot_frame(target_type)
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

    def _spot_frame(self, target_type: TargetType) -> pd.DataFrame:
        if target_type not in self._spot_frames:
            self._spot_frames[target_type] = self._stock_spot_func() if target_type == "stock" else self._index_spot_func()
        return self._spot_frames[target_type]

    def _find_row(self, frame: pd.DataFrame, symbol: str) -> pd.Series:
        if frame.empty or "代码" not in frame.columns:
            raise ValueError(f"No market data found for {symbol}")
        normalized = frame.copy()
        normalized["代码"] = normalized["代码"].astype(str).str.zfill(6)
        matches = normalized[normalized["代码"] == symbol]
        if matches.empty:
            raise ValueError(f"No market data found for {symbol}")
        return matches.iloc[0]
