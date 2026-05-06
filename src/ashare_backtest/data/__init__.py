# 这里集中导出数据层常用函数
# 其他模块只需要从 data 包导入，不需要关心具体文件位置
from .cleaning import standardize_ashare_daily
from .fetcher import AkshareAStockFetcher
from .repository import (
    list_available_symbols,
    load_daily_bars,
    load_many_daily_bars,
    save_backtest_run,
    upsert_daily_bars,
    upsert_strategy_signals,
)

__all__ = [
    # 抓取器负责向外部数据源要原始数据
    "AkshareAStockFetcher",
    # 下面这些函数负责数据库读写和数据整理
    "list_available_symbols",
    "load_daily_bars",
    "load_many_daily_bars",
    "save_backtest_run",
    "standardize_ashare_daily",
    "upsert_daily_bars",
    "upsert_strategy_signals",
]
