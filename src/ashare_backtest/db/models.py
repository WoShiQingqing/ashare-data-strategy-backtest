# 数据库表结构定义

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class StockDailyBar(Base):
    # A 股日线行情表

    __tablename__ = "stock_daily_bar"

    # 自增主键主要是为了数据库层处理方便
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # symbol + trade_date 才是真正的业务主键
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[Date] = mapped_column(Date, index=True)

    # 下面是最基本的 OHLCV 字段
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)

    # 下面这些字段不是每个源都稳定提供
    # 所以允许为空
    amplitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="akshare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        # 同一只股票同一天只能有一条日线记录
        UniqueConstraint("symbol", "trade_date", name="uq_stock_daily_bar_symbol_date"),
    )


class StrategySignal(Base):
    # 策略信号快照表，用于回溯某天策略给出的仓位建议

    __tablename__ = "strategy_signal"

    # 这里保留 signal 和 score
    # signal 用于回测复现，score 用于后续排序或调试
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    strategy_name: Mapped[str] = mapped_column(String(64), index=True)
    trade_date: Mapped[Date] = mapped_column(Date, index=True)
    signal: Mapped[float] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        # 同一策略在同一股票同一天只保留一条信号
        UniqueConstraint(
            "symbol",
            "strategy_name",
            "trade_date",
            name="uq_strategy_signal_symbol_name_date",
        ),
    )


class BacktestRun(Base):
    # 回测运行摘要表，用于保存每次实验的指标和参数

    __tablename__ = "backtest_run"

    # 这个表不保存逐日明细
    # 它只记录一次回测跑完后的摘要快照
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    strategy_name: Mapped[str] = mapped_column(String(64), index=True)
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)
    annual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
