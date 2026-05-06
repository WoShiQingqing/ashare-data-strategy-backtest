# 均值回归策略

from __future__ import annotations

import pandas as pd

from .base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    # 价格偏离均值过深时买入，回归后离场
    # 这是一个有明显开仓和平仓状态的策略

    name = "mean_reversion"

    def __init__(self, window: int = 20, entry_z: float = 1.5, exit_z: float = 0.5) -> None:
        self.window = window
        self.entry_z = entry_z
        self.exit_z = exit_z

    def generate_signals(self, bars: pd.DataFrame) -> pd.DataFrame:
        self.validate_columns(bars)
        df = bars.copy()
        # 先算滚动均值和滚动波动率
        df["rolling_mean"] = df["close"].rolling(self.window).mean()
        df["rolling_std"] = df["close"].rolling(self.window).std(ddof=0)
        df["z_score"] = ((df["close"] - df["rolling_mean"]) / df["rolling_std"]).fillna(0.0)

        position = 0.0
        signals: list[float] = []
        for z_score in df["z_score"]:
            # 这里用显式状态机写法，便于读懂“开仓”和“平仓”的边界
            if z_score <= -self.entry_z:
                # 偏离均值太深时入场
                position = 1.0
            elif z_score >= -self.exit_z:
                # 回到均值附近时离场
                position = 0.0
            signals.append(position)

        df["signal"] = signals
        df["score"] = -df["z_score"]
        df["strategy_name"] = self.name
        return df

    @property
    def parameters(self) -> dict[str, object]:
        # 这些参数决定了进出场边界
        return {
            "window": self.window,
            "entry_z": self.entry_z,
            "exit_z": self.exit_z,
        }
