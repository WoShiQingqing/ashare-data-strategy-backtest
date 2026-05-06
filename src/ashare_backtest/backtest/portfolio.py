# 组合回测引擎

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ashare_backtest.backtest.metrics import annual_return, max_drawdown, sharpe_ratio


@dataclass
class PortfolioBacktestResult:
    # 组合回测输出结果
    # portfolio_frame 是组合层逐日结果
    # constituent_frames 是每个成分股自己的回测结果
    # metrics 是组合层最终指标

    portfolio_frame: pd.DataFrame
    constituent_frames: dict[str, pd.DataFrame]
    metrics: dict[str, float]


class PortfolioBacktestEngine:
    # 把多只股票的单标的结果汇总成组合净值
    # 这里不重新跑单标的策略逻辑
    # 它假设传进来的 constituent_frames 已经是回测后的日度结果

    def run(
        self,
        constituent_frames: dict[str, pd.DataFrame],
        fee_rate: float = 0.0005,
        slippage_rate: float = 0.0002,
    ) -> PortfolioBacktestResult:
        if not constituent_frames:
            raise ValueError("组合回测至少需要一个标的")

        valid_frames = {
            symbol: frame.copy().sort_values("trade_date").reset_index(drop=True)
            for symbol, frame in constituent_frames.items()
            if not frame.empty
        }
        if not valid_frames:
            raise ValueError("组合回测输入全为空")

        # 先把每只股票的收益和持仓对齐到同一时间轴
        returns_frames = []
        position_frames = []
        for symbol, frame in valid_frames.items():
            if "asset_return" not in frame.columns or "position" not in frame.columns:
                raise ValueError(f"{symbol} 的回测结果缺少 asset_return 或 position")

            # 这里拆成两张表
            # 一张只放收益，一张只放持仓，后面组合计算更清楚
            returns_frames.append(
                frame.loc[:, ["trade_date", "asset_return"]].rename(columns={"asset_return": symbol})
            )
            position_frames.append(
                frame.loc[:, ["trade_date", "position"]].rename(columns={"position": symbol})
            )

        returns_pivot = self._merge_frames(returns_frames)
        positions_pivot = self._merge_frames(position_frames)

        # 当前项目采用“对所有有持仓的标的等权分配”的简单组合规则
        active_count = positions_pivot.gt(0).sum(axis=1).replace(0, np.nan)
        target_weights = positions_pivot.div(active_count, axis=0).fillna(0.0)
        turnover = target_weights.diff().abs().sum(axis=1).fillna(target_weights.abs().sum(axis=1))
        cost = turnover * (fee_rate + slippage_rate)

        # 组合收益就是权重乘单日收益再扣成本
        portfolio_return = (target_weights * returns_pivot).sum(axis=1) - cost
        equity_curve = (1.0 + portfolio_return).cumprod()
        drawdown = equity_curve / equity_curve.cummax() - 1.0

        portfolio_frame = pd.DataFrame(
            {
                "trade_date": returns_pivot.index,
                "active_positions": positions_pivot.gt(0).sum(axis=1).astype(int).values,
                "turnover": turnover.values,
                "cost": cost.values,
                "portfolio_return": portfolio_return.values,
                "equity_curve": equity_curve.values,
                "drawdown": drawdown.values,
            }
        ).reset_index(drop=True)

        metrics = {
            # 组合层胜率这里用“单日收益为正的占比”近似
            "annual_return": annual_return(portfolio_return),
            "max_drawdown": max_drawdown(equity_curve),
            "sharpe_ratio": sharpe_ratio(portfolio_return),
            "win_rate": float((portfolio_return > 0).mean()) if len(portfolio_return) else 0.0,
            "turnover_rate": float(turnover.mean()) if len(turnover) else 0.0,
        }

        return PortfolioBacktestResult(
            portfolio_frame=portfolio_frame,
            constituent_frames=valid_frames,
            metrics=metrics,
        )

    @staticmethod
    def _merge_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
        # 按 trade_date 对齐多份结果表
        # 组合回测最重要的前提就是所有标的在同一时间轴上
        merged = None
        for frame in frames:
            current = frame.copy()
            current["trade_date"] = pd.to_datetime(current["trade_date"])
            current = current.set_index("trade_date")
            merged = current if merged is None else merged.join(current, how="outer")
        return merged.sort_index().fillna(0.0)
