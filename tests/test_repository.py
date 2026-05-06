from __future__ import annotations

from datetime import date

import pandas as pd

from ashare_backtest.data.repository import (
    _normalize_date,
    list_available_symbols,
    load_daily_bars,
    save_backtest_run,
    upsert_daily_bars,
    upsert_strategy_signals,
)
from ashare_backtest.db.session import get_engine, init_db


def test_normalize_date_supports_yyyymmdd_string():
    assert _normalize_date("20240131") == "2024-01-31"


def test_can_save_and_load_bars_signals_and_runs():
    engine = get_engine("sqlite:///:memory:")
    init_db(engine)

    bars = pd.DataFrame(
        {
            "symbol": ["600519", "600519"],
            "trade_date": [date(2024, 1, 2), date(2024, 1, 3)],
            "open": [10.0, 10.2],
            "high": [10.3, 10.5],
            "low": [9.9, 10.1],
            "close": [10.1, 10.4],
            "volume": [1000.0, 1200.0],
            "amount": [10000.0, 12000.0],
            "amplitude": [1.0, 1.5],
            "pct_change": [0.5, 2.0],
            "price_change": [0.05, 0.30],
            "turnover_rate": [0.7, 0.9],
            "source": ["akshare", "akshare"],
        }
    )
    assert upsert_daily_bars(bars, engine) == 2

    loaded = load_daily_bars("600519", engine, "20240101", "20240131")
    assert len(loaded) == 2
    assert list_available_symbols(engine) == ["600519"]

    signals = pd.DataFrame(
        {
            "symbol": ["600519", "600519"],
            "strategy_name": ["ma_cross", "ma_cross"],
            "trade_date": [date(2024, 1, 2), date(2024, 1, 3)],
            "signal": [0.0, 1.0],
            "score": [0.0, 0.03],
        }
    )
    assert upsert_strategy_signals(signals, engine) == 2

    save_backtest_run(
        engine=engine,
        symbol="600519",
        strategy_name="ma_cross",
        parameters={"mode": "single"},
        metrics={
            "annual_return": 0.12,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.5,
            "win_rate": 0.55,
            "turnover_rate": 0.2,
        },
    )

    with engine.begin() as connection:
        signal_count = connection.exec_driver_sql("SELECT COUNT(*) FROM strategy_signal").scalar_one()
        run_count = connection.exec_driver_sql("SELECT COUNT(*) FROM backtest_run").scalar_one()

    assert signal_count == 2
    assert run_count == 1
