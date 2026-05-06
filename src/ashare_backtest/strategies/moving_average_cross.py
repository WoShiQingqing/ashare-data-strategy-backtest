# 均线交叉策略

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy


class MovingAverageCrossStrategy(BaseStrategy):
    # 短均线高于长均线时持仓，否则空仓
    # 这类策略逻辑简单，面试时也容易解释清楚

    name = "ma_cross"

    def __init__(self, short_window: int = 5, long_window: int = 20) -> None:
        # 短均线必须比长均线短，否则策略定义本身就不成立
        if short_window >= long_window:
            raise ValueError("short_window 必须小于 long_window")
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, bars: pd.DataFrame) -> pd.DataFrame:
        self.validate_columns(bars)
        df = bars.copy()
        # 先计算两条均线，再把关系转换成 0/1 持仓信号
        df["ma_short"] = df["close"].rolling(self.short_window).mean()
        df["ma_long"] = df["close"].rolling(self.long_window).mean()
        # 短均线在上方时认为趋势更强
        df["signal"] = (df["ma_short"] > df["ma_long"]).astype(float)
        # score 不是硬性必须字段，但保留它更方便调试和排序
        df["score"] = (df["ma_short"] / df["ma_long"] - 1.0).fillna(0.0)
        df["strategy_name"] = self.name
        return df

    @property
    def parameters(self) -> dict[str, object]:
        # 回测结果落库时会把参数一起写进去
        return {"short_window": self.short_window, "long_window": self.long_window}
