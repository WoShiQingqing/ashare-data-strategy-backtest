# 回测指标计算函数

from __future__ import annotations

import numpy as np
import pandas as pd


def annual_return(returns: pd.Series, trading_days: int = 252) -> float:
    # 根据日收益序列计算年化收益
    # 这里按 252 个交易日做年化
    if returns.empty:
        return 0.0
    total_return = float((1.0 + returns).prod())
    years = len(returns) / trading_days
    if years <= 0:
        return 0.0
    return total_return ** (1.0 / years) - 1.0


def max_drawdown(equity_curve: pd.Series) -> float:
    # 计算净值曲线最大回撤
    # 返回值为负数，越小表示回撤越深
    if equity_curve.empty:
        return 0.0
    running_peak = equity_curve.cummax()
    drawdown = equity_curve / running_peak - 1.0
    return float(drawdown.min())


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    trading_days: int = 252,
) -> float:
    # 计算简化版年化 Sharpe
    # 这里假设无风险利率按年化均匀分摊到日收益
    if returns.empty:
        return 0.0
    excess_returns = returns - risk_free_rate / trading_days
    std = float(excess_returns.std(ddof=0))
    if std == 0.0:
        return 0.0
    return float(excess_returns.mean() / std * np.sqrt(trading_days))   


def turnover_rate(position: pd.Series) -> float:
    # 用持仓变化幅度近似换手率
    # 教学项目里用这个定义足够直观
    if position.empty:
        return 0.0
    turnover = position.diff().abs().fillna(position.abs())
    return float(turnover.mean())


def trade_win_rate(trades: pd.DataFrame) -> float:
    # 统计已平仓交易中的胜率
    # 未平仓交易不纳入胜率统计
    if trades.empty:
        return 0.0
    closed = trades[trades["status"] == "closed"]
    if closed.empty:
        return 0.0
    return float((closed["pnl_pct"] > 0).mean())
