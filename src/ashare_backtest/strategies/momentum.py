# 动量策略

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    # 过去一段时间涨幅超过阈值时开仓
    # 它更适合拿来做股票池横向筛选

    name = "momentum"

    def __init__(self, lookback: int = 20, threshold: float = 0.03) -> None:
        self.lookback = lookback
        self.threshold = threshold

    def generate_signals(self, bars: pd.DataFrame) -> pd.DataFrame:
        self.validate_columns(bars)
        df = bars.copy()
        # 用固定回看窗口计算价格动量
        df["momentum"] = df["close"].pct_change(self.lookback)
        # 动量高于阈值时给出持仓信号
        df["signal"] = (df["momentum"] > self.threshold).astype(float)
        df["score"] = df["momentum"].fillna(0.0)
        df["strategy_name"] = self.name
        return df

    @property
    def parameters(self) -> dict[str, object]:
        # 参数单独暴露，便于 CLI 和回测报告统一记录
        return {"lookback": self.lookback, "threshold": self.threshold}
