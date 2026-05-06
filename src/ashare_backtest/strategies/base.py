# 策略抽象基类

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    # 所有策略都需要继承的统一接口

    name = "base"

    @abstractmethod
    def generate_signals(self, bars: pd.DataFrame) -> pd.DataFrame:
        # 根据行情生成带 signal 字段的结果表
        raise NotImplementedError

    @staticmethod
    def validate_columns(bars: pd.DataFrame) -> None:
        # 检查策略最基本的输入字段
        required = {"trade_date", "close"}
        missing = required - set(bars.columns)
        if missing:
            raise ValueError(f"策略输入数据缺少字段: {sorted(missing)}")

    @property
    def parameters(self) -> dict[str, object]:
        # 返回策略当前参数，便于落库和报告输出
        return {}
