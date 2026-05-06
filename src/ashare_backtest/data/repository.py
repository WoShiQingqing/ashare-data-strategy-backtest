# 数据层仓库函数，负责数据库读写

from __future__ import annotations

from datetime import date
import json

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def _normalize_date(value: str | date | None) -> str | None:
    # 统一日期格式，兼容 YYYYMMDD 和 YYYY-MM-DD
    # CLI、数据库和 pandas 在日期格式上经常不一致
    # 这个函数就是用来兜这一层转换
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    text_value = str(value)
    if len(text_value) == 8 and text_value.isdigit():
        return pd.to_datetime(text_value, format="%Y%m%d").strftime("%Y-%m-%d")
    return text_value


def upsert_daily_bars(df: pd.DataFrame, engine: Engine) -> int:
    # 按 symbol + 日期区间覆盖写入日线数据
    # 这比逐行判断是否存在更简单，足够应付当前日频项目
    if df.empty:
        return 0

    symbol = df["symbol"].iloc[0]
    start_date = _normalize_date(df["trade_date"].min())
    end_date = _normalize_date(df["trade_date"].max())

    with engine.begin() as connection:
        # 当前项目先用“删区间再插入”的简单 upsert 策略
        # 这样代码可读性高，数据库也容易排错
        connection.execute(
            text(
                """
                DELETE FROM stock_daily_bar
                WHERE symbol = :symbol
                  AND trade_date BETWEEN :start_date AND :end_date
                """
            ),
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        )
        df.to_sql("stock_daily_bar", con=connection, if_exists="append", index=False)

    return len(df)


def load_daily_bars(
    symbol: str,
    engine: Engine,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    # 读取单只股票的日线数据
    # 回测前的数据入口基本都走这里
    query = """
        SELECT symbol, trade_date, open, high, low, close, volume, amount,
               amplitude, pct_change, price_change, turnover_rate, source
        FROM stock_daily_bar
        WHERE symbol = :symbol
    """
    params: dict[str, str] = {"symbol": str(symbol).zfill(6)}

    if start_date:
        query += " AND trade_date >= :start_date"
        params["start_date"] = _normalize_date(start_date) or ""
    if end_date:
        query += " AND trade_date <= :end_date"
        params["end_date"] = _normalize_date(end_date) or ""

    query += " ORDER BY trade_date"

    with engine.begin() as connection:
        df = pd.read_sql(text(query), con=connection, params=params)

    if df.empty:
        return df

    # 统一回转成 pandas 时间戳
    # 策略和画图阶段都更好用
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.sort_values("trade_date").reset_index(drop=True)


def load_many_daily_bars(
    symbols: list[str],
    engine: Engine,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, pd.DataFrame]:
    # 批量读取多只股票日线，并按 symbol 返回
    # 组合回测会直接消费这个返回结构
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
    # 列出数据库里已经入库的股票代码
    # 这个接口主要给 CLI 菜单和 list-symbols 命令用
    query = text(
        """
        SELECT DISTINCT symbol
        FROM stock_daily_bar
        ORDER BY symbol
        """
    )
    with engine.begin() as connection:
        rows = connection.execute(query).fetchall()
    return [row[0] for row in rows]


def upsert_strategy_signals(df: pd.DataFrame, engine: Engine) -> int:
    # 保存策略信号快照，便于回看历史信号
    # 信号单独落库后，后面想查某只股票某天为什么开仓会容易很多
    if df.empty:
        return 0

    required = {"symbol", "strategy_name", "trade_date", "signal", "score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"策略信号缺少字段: {sorted(missing)}")

    payload = df[list(required)].copy()
    payload["trade_date"] = pd.to_datetime(payload["trade_date"]).dt.date

    symbol = payload["symbol"].iloc[0]
    strategy_name = payload["strategy_name"].iloc[0]
    start_date = _normalize_date(payload["trade_date"].min())
    end_date = _normalize_date(payload["trade_date"].max())

    with engine.begin() as connection:
        # 同一只股票、同一策略、同一天只保留一条信号记录
        # 先删后插可以避免重复键冲突
        connection.execute(
            text(
                """
                DELETE FROM strategy_signal
                WHERE symbol = :symbol
                  AND strategy_name = :strategy_name
                  AND trade_date BETWEEN :start_date AND :end_date
                """
            ),
            {
                "symbol": symbol,
                "strategy_name": strategy_name,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        payload.to_sql("strategy_signal", con=connection, if_exists="append", index=False)

    return len(payload)


def save_backtest_run(
    engine: Engine,
    symbol: str,
    strategy_name: str,
    parameters: dict[str, object],
    metrics: dict[str, float],
) -> None:
    # 保存一次回测运行的摘要指标
    # 这样即使你后面删了图表文件，数据库里也还有实验历史
    payload = {
        "symbol": symbol,
        "strategy_name": strategy_name,
        "parameters": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
        "annual_return": metrics.get("annual_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
        "win_rate": metrics.get("win_rate"),
        "turnover_rate": metrics.get("turnover_rate"),
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO backtest_run (
                    symbol, strategy_name, parameters,
                    annual_return, max_drawdown, sharpe_ratio, win_rate, turnover_rate
                ) VALUES (
                    :symbol, :strategy_name, :parameters,
                    :annual_return, :max_drawdown, :sharpe_ratio, :win_rate, :turnover_rate
                )
                """
            ),
            payload,
        )
