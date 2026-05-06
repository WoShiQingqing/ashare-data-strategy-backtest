# 策略注册表

from __future__ import annotations

import inspect

from ashare_backtest.strategies.bollinger_band import BollingerBandStrategy
from ashare_backtest.strategies.mean_reversion import MeanReversionStrategy
from ashare_backtest.strategies.momentum import MomentumStrategy
from ashare_backtest.strategies.moving_average_cross import MovingAverageCrossStrategy


STRATEGY_MAPPING = {
    # 所有 CLI 可选策略都集中在这里，新增策略时优先改这个映射
    "ma_cross": MovingAverageCrossStrategy,
    "bollinger_band": BollingerBandStrategy,
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
}


def strategy_choices() -> list[str]:
    # 返回 CLI 可用的策略名列表
    return list(STRATEGY_MAPPING.keys())


def build_strategy(name: str, **kwargs):
    # 按策略名和参数动态创建策略实例
    # CLI 会把很多参数统一传进来
    # 这里负责筛掉当前策略完全不认识的参数
    normalized = name.strip().lower()
    if normalized in STRATEGY_MAPPING:
        strategy_class = STRATEGY_MAPPING[normalized]
        signature = inspect.signature(strategy_class.__init__)
        # 只把该策略构造函数真正需要的参数传进去，避免无关参数报错
        init_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in signature.parameters and value is not None
        }
        return strategy_class(**init_kwargs)

    raise ValueError(
        f"未知策略: {name}. 可选值: {', '.join(strategy_choices())}"
    )
