# 数据库表结构定义
# 这一版不再使用 ORM class
# 直接用 SQLAlchemy Core 的 Table 来描述表结构

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)

from .base import metadata


# A 股日线行情表
# symbol + trade_date 是最重要的业务唯一键
StockDailyBar = Table(
    "stock_daily_bar",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String(16), index=True, nullable=False),
    Column("trade_date", Date, index=True, nullable=False),
    Column("open", Float, nullable=False),
    Column("high", Float, nullable=False),
    Column("low", Float, nullable=False),
    Column("close", Float, nullable=False),
    Column("volume", Float, nullable=False, default=0.0),
    Column("amount", Float, nullable=False, default=0.0),
    Column("amplitude", Float, nullable=True),
    Column("pct_change", Float, nullable=True),
    Column("price_change", Float, nullable=True),
    Column("turnover_rate", Float, nullable=True),
    Column("source", String(32), nullable=False, default="akshare"),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    UniqueConstraint("symbol", "trade_date", name="uq_stock_daily_bar_symbol_date"),
)


# 策略信号快照表
# 用来保留某一天、某个策略到底给出了什么信号
StrategySignal = Table(
    "strategy_signal",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String(16), index=True, nullable=False),
    Column("strategy_name", String(64), index=True, nullable=False),
    Column("trade_date", Date, index=True, nullable=False),
    Column("signal", Float, nullable=False),
    Column("score", Float, nullable=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    UniqueConstraint(
        "symbol",
        "strategy_name",
        "trade_date",
        name="uq_strategy_signal_symbol_name_date",
    ),
)


# 回测运行摘要表
# 只保留每次实验的摘要指标和参数，不保留逐日明细
BacktestRun = Table(
    "backtest_run",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("symbol", String(16), index=True, nullable=False),
    Column("strategy_name", String(64), index=True, nullable=False),
    Column("parameters", Text, nullable=True),
    Column("annual_return", Float, nullable=True),
    Column("max_drawdown", Float, nullable=True),
    Column("sharpe_ratio", Float, nullable=True),
    Column("win_rate", Float, nullable=True),
    Column("turnover_rate", Float, nullable=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
)
