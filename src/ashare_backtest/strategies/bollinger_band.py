# 布林带策略

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy


class BollingerBandStrategy(BaseStrategy):
    # 价格跌破下轨时开仓的简化版布林带策略
    # 这里先保留最直观的定义，方便阅读和展示

    name = "bollinger_band"

    def __init__(self, window: int = 20, num_std: float = 2.0) -> None:
        if window <= 1:
            raise ValueError("window 必须大于 1")
        if num_std <= 0:
            raise ValueError("num_std 必须大于 0")
        self.window = window
        self.num_std = num_std

    def generate_signals(self, bars: pd.DataFrame) -> pd.DataFrame:
        self.validate_columns(bars)
        df = bars.copy()
        # 先算中轨和标准差，再推上轨和下轨
        df["mid"] = df["close"].rolling(self.window).mean()
        df["std"] = df["close"].rolling(self.window).std(ddof=0)
        df["upper"] = df["mid"] + self.num_std * df["std"]
        df["lower"] = df["mid"] - self.num_std * df["std"]

        # 为了保持和其他策略一致，这里仍然输出二值信号
        # 跌破下轨时视为出现反弹观察机会
        raw_signal = (df["close"] < df["lower"]).astype(float)
        df["signal"] = raw_signal.fillna(0.0)
        df["score"] = ((df["lower"] - df["close"]) / df["close"]).fillna(0.0)
        df["strategy_name"] = self.name
        return df

    @property
    def parameters(self) -> dict[str, object]:
        # 报告层会直接展示这里的参数
        return {"window": self.window, "num_std": self.num_std}
