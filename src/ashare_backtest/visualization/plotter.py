# 回测图表输出

from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


class BacktestPlotter:
    # 负责把回测结果保存成静态图表

    def __init__(self, output_dir: Path | str = "output/plots") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot(self, result_frame: pd.DataFrame, symbol: str, strategy_name: str) -> Path:
        # 绘制单标的净值、回撤和买卖点图
        figure, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

        axes[0].plot(result_frame["trade_date"], result_frame["equity_curve"], label="equity")
        axes[0].set_title(f"{symbol} - {strategy_name} equity curve")
        axes[0].legend(loc="upper left")

        axes[1].fill_between(
            result_frame["trade_date"],
            result_frame["drawdown"],
            0,
            color="tomato",
            alpha=0.35,
        )
        axes[1].set_title("drawdown")

        axes[2].plot(result_frame["trade_date"], result_frame["close"], label="close", color="steelblue")
        buy_points = result_frame[result_frame["position"].diff().fillna(result_frame["position"]) > 0]
        sell_points = result_frame[result_frame["position"].diff().fillna(0.0) < 0]
        axes[2].scatter(buy_points["trade_date"], buy_points["close"], marker="^", color="red", label="buy")
        axes[2].scatter(sell_points["trade_date"], sell_points["close"], marker="v", color="green", label="sell")
        axes[2].set_title("price and signals")
        axes[2].legend(loc="upper left")

        figure.tight_layout()
        output_path = self.output_dir / f"{symbol}_{strategy_name}_report.png"
        figure.savefig(output_path, dpi=150)
        plt.close(figure)
        return output_path

    def plot_portfolio(
        self,
        portfolio_frame: pd.DataFrame,
        portfolio_name: str,
        strategy_name: str,
    ) -> Path:
        # 绘制组合净值和组合回撤图
        figure, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        axes[0].plot(
            portfolio_frame["trade_date"],
            portfolio_frame["equity_curve"],
            label="portfolio equity",
            color="navy",
        )
        axes[0].set_title(f"{portfolio_name} - {strategy_name} portfolio equity curve")
        axes[0].legend(loc="upper left")

        axes[1].fill_between(
            portfolio_frame["trade_date"],
            portfolio_frame["drawdown"],
            0,
            color="tomato",
            alpha=0.35,
            label="drawdown",
        )
        axes[1].set_title("portfolio drawdown")
        axes[1].legend(loc="upper left")

        figure.tight_layout()
        output_path = self.output_dir / f"{portfolio_name}_{strategy_name}_portfolio.png"
        figure.savefig(output_path, dpi=150)
        plt.close(figure)
        return output_path
