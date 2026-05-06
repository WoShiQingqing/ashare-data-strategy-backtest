# 回测报告输出

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


class ReportWriter:
    # 负责把回测结果保存成 JSON / CSV 报告
    # 这一层单独拆出来后，后面改 Excel 或网页输出会更方便

    def __init__(self, output_dir: Path | str = "output/reports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_single_backtest(
        self,
        symbol: str,
        strategy_name: str,
        metrics: dict[str, float],
        result_frame: pd.DataFrame,
        trades: pd.DataFrame,
        extra: dict[str, object] | None = None,
    ) -> dict[str, str]:
        # 保存单标的回测摘要、日度结果和交易明细
        # 同一个前缀下放 3 类文件，人工查看时比较直观
        prefix = f"{symbol}_{strategy_name}"
        report_payload = {
            "symbol": symbol,
            "strategy_name": strategy_name,
            "metrics": metrics,
            "extra": extra or {},
        }
        summary_path = self.output_dir / f"{prefix}_summary.json"
        daily_path = self.output_dir / f"{prefix}_daily.csv"
        trades_path = self.output_dir / f"{prefix}_trades.csv"

        summary_path.write_text(
            json.dumps(report_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result_frame.to_csv(daily_path, index=False)
        trades.to_csv(trades_path, index=False)
        return {
            "summary": str(summary_path),
            "daily": str(daily_path),
            "trades": str(trades_path),
        }

    def save_portfolio_backtest(
        self,
        portfolio_name: str,
        strategy_name: str,
        metrics: dict[str, float],
        portfolio_frame: pd.DataFrame,
        constituents: dict[str, pd.DataFrame],
        extra: dict[str, object] | None = None,
    ) -> dict[str, str]:
        # 保存组合回测摘要、组合日度结果和成分说明
        # 成分文件单独保存，是为了让人一眼看清组合里到底有哪些股票
        prefix = f"{portfolio_name}_{strategy_name}"
        summary_path = self.output_dir / f"{prefix}_summary.json"
        daily_path = self.output_dir / f"{prefix}_portfolio_daily.csv"
        members_path = self.output_dir / f"{prefix}_constituents.json"

        summary_payload = {
            "portfolio_name": portfolio_name,
            "strategy_name": strategy_name,
            "metrics": metrics,
            "extra": extra or {},
            "symbols": sorted(constituents.keys()),
        }
        members_payload = {
            symbol: {
                "rows": int(len(frame)),
                "start_date": pd.to_datetime(frame["trade_date"]).min().strftime("%Y-%m-%d"),
                "end_date": pd.to_datetime(frame["trade_date"]).max().strftime("%Y-%m-%d"),
            }
            for symbol, frame in constituents.items()
        }

        summary_path.write_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        daily_path.write_text(portfolio_frame.to_csv(index=False), encoding="utf-8")
        members_path.write_text(
            json.dumps(members_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "summary": str(summary_path),
            "daily": str(daily_path),
            "constituents": str(members_path),
        }
