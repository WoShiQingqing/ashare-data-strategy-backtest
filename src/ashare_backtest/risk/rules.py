# 风控规则

from __future__ import annotations

import pandas as pd


def enforce_risk_limits(
    close: pd.Series,
    desired_position: pd.Series,
    max_position: float = 1.0,
    stop_loss: float = 0.08,
    max_drawdown_limit: float = 0.15,
) -> pd.DataFrame:
    # 根据目标仓位生成受风控约束后的真实持仓
    prices = close.astype(float).reset_index(drop=True)
    desired = desired_position.fillna(0.0).clip(lower=0.0, upper=max_position).reset_index(drop=True)

    positions: list[float] = []
    events: list[str] = []

    current_position = 0.0
    entry_price: float | None = None
    equity = 1.0
    peak_equity = 1.0
    previous_price: float | None = None

    for current_price, target_position in zip(prices, desired):
        forced_exit = False

        if previous_price is not None:
            # 先根据昨日持仓更新当前资金曲线，便于后面判断回撤
            daily_return = current_price / previous_price - 1.0
            equity *= 1.0 + current_position * daily_return
            peak_equity = max(peak_equity, equity)

        previous_price = current_price
        event = "hold"

        if current_position > 0.0 and entry_price is not None:
            trade_return = current_price / entry_price - 1.0
            drawdown = equity / peak_equity - 1.0
            if trade_return <= -stop_loss:
                # 单笔亏损超过阈值则强制平仓
                current_position = 0.0
                entry_price = None
                forced_exit = True
                event = "stop_loss"
            elif drawdown <= -max_drawdown_limit:
                # 资金曲线从峰值回撤过深时熔断离场
                current_position = 0.0
                entry_price = None
                forced_exit = True
                event = "max_drawdown"

        if current_position == 0.0 and target_position > 0.0 and not forced_exit:
            # 仅在没有被风控强平的情况下允许新开仓
            current_position = float(target_position)
            entry_price = float(current_price)
            event = "entry"
        elif current_position > 0.0 and target_position == 0.0:
            current_position = 0.0
            entry_price = None
            event = "exit"

        positions.append(current_position)
        events.append(event)

    return pd.DataFrame({"position": positions, "risk_event": events})
