# 数据库层对外导出
# 这里暴露的是 Core 表对象，不再是 ORM 模型类

from .base import metadata
from .models import BacktestRun, StockDailyBar, StrategySignal
from .session import get_engine, get_session_factory, init_db

__all__ = [
    "metadata",
    "BacktestRun",
    "StockDailyBar",
    "StrategySignal",
    "get_engine",
    "get_session_factory",
    "init_db",
]
