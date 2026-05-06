import pandas as pd

from ashare_backtest.backtest.metrics import annual_return, max_drawdown, sharpe_ratio


def test_max_drawdown_is_negative_when_curve_drops():
    equity_curve = pd.Series([1.0, 1.1, 1.05, 0.9, 0.95])
    assert round(max_drawdown(equity_curve), 4) == -0.1818


def test_annual_return_and_sharpe_return_numbers():
    returns = pd.Series([0.01, -0.005, 0.02, 0.0, 0.01])
    assert annual_return(returns) > 0
    assert sharpe_ratio(returns) != 0

