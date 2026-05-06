# 单标的回测引擎

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ashare_backtest.backtest.metrics import (
    annual_return,
    max_drawdown,
    sharpe_ratio,
    trade_win_rate,
    turnover_rate,
)
from ashare_backtest.risk.rules import enforce_risk_limits


@dataclass
class BacktestResult:
    # 单次回测输出结果
    # result_frame 是逐日结果
    # trades 是抽出来的交易记录
    # metrics 是最终摘要指标

    result_frame: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


class BacktestEngine:
    # 把策略信号转换为净值曲线和交易记录
    # 这个类不负责抓数，也不负责画图
    # 它只关心一件事，就是收益怎么算

    def run(
        self,
        strategy_frame: pd.DataFrame,
        fee_rate: float = 0.0005,
        slippage_rate: float = 0.0002,
        max_position: float = 1.0,
        stop_loss: float = 0.08,
        max_drawdown_limit: float = 0.15,
    ) -> BacktestResult:
        if strategy_frame.empty:
            raise ValueError("回测输入为空")

        # 回测前先复制一份，避免污染原始策略结果
        df = strategy_frame.copy().sort_values("trade_date").reset_index(drop=True)
        if "signal" not in df.columns:
            raise ValueError("回测输入缺少 signal 字段")

        # 先计算标的自身收益，再将策略信号滞后一天映射成实际持仓
        # 这里滞后一天是为了避免今天收盘算出的信号立刻用在今天收益上
        df["asset_return"] = df["close"].pct_change().fillna(0.0)
        df["desired_position"] = df["signal"].shift(1).fillna(0.0)

        # 风控模块有权否决目标持仓，例如止损或回撤熔断
        risk_frame = enforce_risk_limits(
            close=df["close"],
            desired_position=df["desired_position"],
            max_position=max_position,
            stop_loss=stop_loss,
            max_drawdown_limit=max_drawdown_limit,
        )

        df["position"] = risk_frame["position"]
        df["risk_event"] = risk_frame["risk_event"]

        # turnover 用来近似交易频率
        # 每次仓位变化都会产生交易成本
        df["turnover"] = df["position"].diff().abs().fillna(df["position"].abs())
        df["cost"] = df["turnover"] * (fee_rate + slippage_rate)
        # 策略收益 = 持仓收益 - 交易成本
        df["strategy_return"] = df["position"] * df["asset_return"] - df["cost"]
        df["equity_curve"] = (1.0 + df["strategy_return"]).cumprod()
        df["drawdown"] = df["equity_curve"] / df["equity_curve"].cummax() - 1.0

        trades = self._extract_trades(df, fee_rate, slippage_rate)

        # 把常用指标集中算好，CLI 和报告层直接拿去展示
        metrics = {
            "annual_return": annual_return(df["strategy_return"]),
            "max_drawdown": max_drawdown(df["equity_curve"]),
            "sharpe_ratio": sharpe_ratio(df["strategy_return"]),
            "win_rate": trade_win_rate(trades),
            "turnover_rate": turnover_rate(df["position"]),
        }

        return BacktestResult(result_frame=df, trades=trades, metrics=metrics)

    @staticmethod
    def _extract_trades(
        result_frame: pd.DataFrame,
        fee_rate: float,
        slippage_rate: float,
    ) -> pd.DataFrame:
        # 从日度持仓轨迹中抽取开平仓交易
        # 这样用户看到的不只是净值曲线，还能看到每笔交易长什么样
        records: list[dict[str, object]] = []
        entry_date = None
        entry_price = None

        # previous_positions 用来判断某天到底是开仓、持有还是平仓
        positions = result_frame["position"].fillna(0.0)
        previous_positions = positions.shift(1).fillna(0.0)

        for row, prev_position in zip(result_frame.itertuples(index=False), previous_positions):
            if prev_position == 0.0 and row.position > 0.0:
                # 从空仓切到持仓，记为开仓
                entry_date = row.trade_date
                entry_price = float(row.close) * (1.0 + slippage_rate + fee_rate)
                continue

            if prev_position > 0.0 and row.position == 0.0 and entry_price is not None:
                # 从持仓切到空仓，记为平仓
                exit_price = float(row.close) * (1.0 - slippage_rate - fee_rate)
                pnl_pct = exit_price / entry_price - 1.0
                records.append(
                    {
                        "entry_date": entry_date,
                        "exit_date": row.trade_date,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_pct": pnl_pct,
                        "status": "closed",
                    }
                )
                entry_date = None
                entry_price = None

        if entry_price is not None:
            # 如果最后一天还没平仓，就把它标成 open
            last_row = result_frame.iloc[-1]
            records.append(
                {
                    "entry_date": entry_date,
                    "exit_date": last_row["trade_date"],
                    "entry_price": entry_price,
                    "exit_price": float(last_row["close"]),
                    "pnl_pct": float(last_row["close"] / entry_price - 1.0),
                    "status": "open",
                }
            )

        return pd.DataFrame(records)
