# 数据层仓库函数
# 这一层专门负责数据库读写
# 现在统一使用 SQLAlchemy Core 的 Table 和语句构造器
# 不再混用 ORM 风格或者手写文本 SQL

from __future__ import annotations

from datetime import date
import json

import pandas as pd
from sqlalchemy import delete, distinct, insert, select
from sqlalchemy.engine import Engine

from ashare_backtest.db import BacktestRun, StockDailyBar, StrategySignal


def _normalize_date(value: str | date | None) -> str | None:
    # 统一日期字符串格式
    # 主要给 CLI 输入和日志输出用
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    text_value = str(value)
    if len(text_value) == 8 and text_value.isdigit():
        return pd.to_datetime(text_value, format="%Y%m%d").strftime("%Y-%m-%d")
    return text_value


def _to_python_date(value: str | date | None) -> date | None:
    # 把外部传进来的日期统一转成 Python date
    # Core 的 Date 列直接配合 date 对象最稳妥
    normalized = _normalize_date(value)
    if normalized is None:
        return None
    return pd.to_datetime(normalized).date()


def _frame_to_records(df: pd.DataFrame, columns: list[str]) -> list[dict[str, object]]:
    # 把 DataFrame 转成适合 Core insert 的记录列表
    # 同时把 NaN 清成 None 避免数据库层出现奇怪空值表现
    payload = df.loc[:, columns].copy()
    payload = payload.where(pd.notna(payload), None)
    if "trade_date" in payload.columns:
        payload["trade_date"] = pd.to_datetime(payload["trade_date"]).dt.date
    return payload.to_dict(orient="records")


def upsert_daily_bars(df: pd.DataFrame, engine: Engine) -> int:
    # 按 symbol 和日期区间覆盖写入日线
    # 这里依然采用先删后插的简单策略
    # 对日频项目来说可读性和稳定性比复杂 upsert 更重要
    if df.empty:
        return 0

    symbol = str(df["symbol"].iloc[0]).zfill(6)
    start_date = _to_python_date(df["trade_date"].min())
    end_date = _to_python_date(df["trade_date"].max())
    records = _frame_to_records(
        df.assign(symbol=symbol),
        [
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
        ],
    )

    with engine.begin() as connection:
        # 先删掉同一只股票在这段区间内的旧数据
        # 再整体插入新数据
        connection.execute(
            delete(StockDailyBar).where(
                StockDailyBar.c.symbol == symbol,
                StockDailyBar.c.trade_date.between(start_date, end_date),
            )
        )
        connection.execute(insert(StockDailyBar), records)

    return len(records)


def load_daily_bars(
    symbol: str,
    engine: Engine,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    # 读取单只股票日线
    # 回测前的数据入口基本都会经过这里
    normalized_symbol = str(symbol).zfill(6)
    stmt = (
        select(
            StockDailyBar.c.symbol,
            StockDailyBar.c.trade_date,
            StockDailyBar.c.open,
            StockDailyBar.c.high,
            StockDailyBar.c.low,
            StockDailyBar.c.close,
            StockDailyBar.c.volume,
            StockDailyBar.c.amount,
            StockDailyBar.c.amplitude,
            StockDailyBar.c.pct_change,
            StockDailyBar.c.price_change,
            StockDailyBar.c.turnover_rate,
            StockDailyBar.c.source,
        )
        .where(StockDailyBar.c.symbol == normalized_symbol)
        .order_by(StockDailyBar.c.trade_date)
    )

    if start_date:
        stmt = stmt.where(StockDailyBar.c.trade_date >= _to_python_date(start_date))
    if end_date:
        stmt = stmt.where(StockDailyBar.c.trade_date <= _to_python_date(end_date))

    with engine.begin() as connection:
        rows = connection.execute(stmt).mappings().all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # 统一转回 pandas 时间戳
    # 策略层和画图层处理起来会更顺手
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.sort_values("trade_date").reset_index(drop=True)


def load_many_daily_bars(
    symbols: list[str],
    engine: Engine,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, pd.DataFrame]:
    # 批量读取多只股票日线
    # 这里继续返回按 symbol 分组的字典
    # 这样组合回测层不需要关心数据库细节
    return {
        str(symbol).zfill(6): load_daily_bars(
            symbol=symbol,
            engine=engine,
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in symbols
    }


def list_available_symbols(engine: Engine) -> list[str]:
    # 列出已经入库的股票代码
    stmt = select(distinct(StockDailyBar.c.symbol)).order_by(StockDailyBar.c.symbol)
    with engine.begin() as connection:
        rows = connection.execute(stmt).all()
    return [row[0] for row in rows]


def upsert_strategy_signals(df: pd.DataFrame, engine: Engine) -> int:
    # 保存策略信号快照
    # 这样后面既能回测也能单独复盘信号本身
    if df.empty:
        return 0

    required = {"symbol", "strategy_name", "trade_date", "signal", "score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"策略信号缺少字段: {sorted(missing)}")

    payload = df.loc[:, ["symbol", "strategy_name", "trade_date", "signal", "score"]].copy()
    payload["symbol"] = payload["symbol"].astype(str).str.zfill(6)

    symbol = payload["symbol"].iloc[0]
    strategy_name = str(payload["strategy_name"].iloc[0])
    start_date = _to_python_date(payload["trade_date"].min())
    end_date = _to_python_date(payload["trade_date"].max())
    records = _frame_to_records(payload, ["symbol", "strategy_name", "trade_date", "signal", "score"])

    with engine.begin() as connection:
        # 同一只股票同一套策略在同一天只保留一条快照
        connection.execute(
            delete(StrategySignal).where(
                StrategySignal.c.symbol == symbol,
                StrategySignal.c.strategy_name == strategy_name,
                StrategySignal.c.trade_date.between(start_date, end_date),
            )
        )
        connection.execute(insert(StrategySignal), records)

    return len(records)


def save_backtest_run(
    engine: Engine,
    symbol: str,
    strategy_name: str,
    parameters: dict[str, object],
    metrics: dict[str, float],
) -> None:
    # 保存一次回测摘要
    # 这里只存概览指标和参数
    # 不把逐日明细全部塞进数据库
    payload = {
        "symbol": str(symbol),
        "strategy_name": str(strategy_name),
        "parameters": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
        "annual_return": metrics.get("annual_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
        "win_rate": metrics.get("win_rate"),
        "turnover_rate": metrics.get("turnover_rate"),
    }
    with engine.begin() as connection:
        connection.execute(insert(BacktestRun).values(**payload))
