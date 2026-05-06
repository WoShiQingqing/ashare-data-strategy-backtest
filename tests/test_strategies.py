import pandas as pd

from ashare_backtest.strategies import (
    BollingerBandStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    MovingAverageCrossStrategy,
)
from ashare_backtest.strategies.registry import build_strategy


def _build_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2024-01-01", periods=40, freq="D"),
            "close": [10 + idx * 0.2 for idx in range(40)],
        }
    )


def test_ma_cross_generates_signal_column():
    result = MovingAverageCrossStrategy(short_window=3, long_window=5).generate_signals(_build_bars())
    assert "signal" in result.columns
    assert result["signal"].iloc[-1] == 1.0


def test_momentum_generates_positive_score_on_uptrend():
    result = MomentumStrategy(lookback=5, threshold=0.01).generate_signals(_build_bars())
    assert result["score"].iloc[-1] > 0


def test_mean_reversion_outputs_binary_signal():
    result = MeanReversionStrategy(window=5, entry_z=0.5, exit_z=0.2).generate_signals(_build_bars())
    assert set(result["signal"].dropna().unique()).issubset({0.0, 1.0})


def test_bollinger_band_generates_required_columns():
    result = BollingerBandStrategy(window=5, num_std=1.0).generate_signals(_build_bars())
    assert "signal" in result.columns
    assert "score" in result.columns
    assert result["strategy_name"].iloc[-1] == "bollinger_band"
    assert set(result["signal"].dropna().unique()).issubset({0.0, 1.0})


def test_registry_accepts_strategy_parameters():
    strategy = build_strategy("ma_cross", short_window=3, long_window=7, threshold=9.9)
    assert isinstance(strategy, MovingAverageCrossStrategy)
    assert strategy.short_window == 3
    assert strategy.long_window == 7
