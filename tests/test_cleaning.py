import pandas as pd

from ashare_backtest.data.cleaning import standardize_ashare_daily


def test_standardize_ashare_daily_maps_columns():
    raw = pd.DataFrame(
        {
            "日期": ["2024-01-02", "2024-01-03"],
            "开盘": [10.0, 10.2],
            "收盘": [10.1, 10.4],
            "最高": [10.3, 10.6],
            "最低": [9.9, 10.1],
            "成交量": [1000, 1200],
            "成交额": [10000, 12000],
            "振幅": [1.1, 2.0],
            "涨跌幅": [0.5, 2.9],
            "涨跌额": [0.05, 0.3],
            "换手率": [0.7, 0.9],
        }
    )

    result = standardize_ashare_daily(raw, "600519")

    assert list(result.columns) == [
        "symbol",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "amplitude",
        "pct_change",
        "price_change",
        "turnover_rate",
        "source",
    ]
    assert result["symbol"].iloc[0] == "600519"
    assert len(result) == 2

