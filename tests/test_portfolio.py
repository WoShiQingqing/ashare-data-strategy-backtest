from __future__ import annotations

import pandas as pd

from ashare_backtest.backtest.portfolio import PortfolioBacktestEngine


def test_portfolio_backtest_engine_returns_metrics_and_frame():
    engine = PortfolioBacktestEngine()
    dates = pd.date_range("2024-01-01", periods=5, freq="D")

    constituent_frames = {
        "600519": pd.DataFrame(
            {
                "trade_date": dates,
                "asset_return": [0.0, 0.01, 0.02, -0.01, 0.0],
                "position": [0.0, 1.0, 1.0, 1.0, 0.0],
            }
        ),
        "000001": pd.DataFrame(
            {
                "trade_date": dates,
                "asset_return": [0.0, -0.005, 0.01, 0.01, 0.005],
                "position": [0.0, 0.0, 1.0, 1.0, 1.0],
            }
        ),
    }

    result = engine.run(constituent_frames, fee_rate=0.0, slippage_rate=0.0)

    assert "equity_curve" in result.portfolio_frame.columns
    assert "drawdown" in result.portfolio_frame.columns
    assert len(result.portfolio_frame) == 5
    assert set(result.constituent_frames.keys()) == {"600519", "000001"}
    assert result.metrics["turnover_rate"] >= 0.0
