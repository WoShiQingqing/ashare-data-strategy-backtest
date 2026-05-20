# 数据层仓库函数
# 这一层专门负责数据库读写
# 表结构定义仍然放在 db/models.py 里
# 但真正的增删改查这里统一写成原生 SQL 语句形式
# 这样查库和写库的意图会更直接

from __future__ import annotations

from datetime import date
import json

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


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
    # 把外部日期统一转成 Python date
    # 这样 SQL 参数在 SQLite 和 MySQL 下都更稳妥
    normalized = _normalize_date(value)
    if normalized is None:
        return None
    return pd.to_datetime(normalized).date()


def _frame_to_records(df: pd.DataFrame, columns: list[str]) -> list[dict[str, object]]:
    # 把 DataFrame 转成数据库批量写入需要的记录列表
    # 同时把 NaN 清成 None 避免数据库里出现奇怪空值
    payload = df.loc[:, columns].copy()
    payload = payload.where(pd.notna(payload), None)
    if "trade_date" in payload.columns:
        payload["trade_date"] = pd.to_datetime(payload["trade_date"]).dt.date
    return payload.to_dict(orient="records")


def upsert_daily_bars(df: pd.DataFrame, engine: Engine) -> int:
    # 按 symbol 和日期区间覆盖写入日线
    # 这里继续采用先删后插的简单策略
    # 日频项目优先追求可读性和稳定性
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

    delete_sql = text(
        """
        DELETE FROM stock_daily_bar
        WHERE symbol = :symbol
          AND trade_date BETWEEN :start_date AND :end_date
        """
    )
    insert_sql = text(
        """
        INSERT INTO stock_daily_bar (
            symbol, trade_date, open, high, low, close,
            volume, amount, amplitude, pct_change,
            price_change, turnover_rate, source
        ) VALUES (
            :symbol, :trade_date, :open, :high, :low, :close,
            :volume, :amount, :amplitude, :pct_change,
            :price_change, :turnover_rate, :source
        )
        """
    )

    with engine.begin() as connection:
        # 先删掉同一只股票在这段区间内的旧数据
        # 再整体插入新数据
        connection.execute(
            delete_sql,
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        )
        connection.execute(insert_sql, records)

    return len(records)


def load_daily_bars(
    symbol: str,
    engine: Engine,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    # 读取单只股票日线
    # 回测前的数据入口基本都会经过这里
    query = """
        SELECT symbol, trade_date, open, high, low, close, volume, amount,
               amplitude, pct_change, price_change, turnover_rate, source
        FROM stock_daily_bar
        WHERE symbol = :symbol
    """
    params: dict[str, object] = {"symbol": str(symbol).zfill(6)}

    if start_date:
        query += " AND trade_date >= :start_date"
        params["start_date"] = _to_python_date(start_date)
    if end_date:
        query += " AND trade_date <= :end_date"
        params["end_date"] = _to_python_date(end_date)

    query += " ORDER BY trade_date"

    with engine.begin() as connection:
        df = pd.read_sql(text(query), con=connection, params=params)

    if df.empty:
        return df

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
    # 继续返回按 symbol 分组的字典
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

    delete_sql = text(
        """
        DELETE FROM strategy_signal
        WHERE symbol = :symbol
          AND strategy_name = :strategy_name
          AND trade_date BETWEEN :start_date AND :end_date
        """
    )
    insert_sql = text(
        """
        INSERT INTO strategy_signal (
            symbol, strategy_name, trade_date, signal, score
        ) VALUES (
            :symbol, :strategy_name, :trade_date, :signal, :score
        )
        """
    )

    with engine.begin() as connection:
        # 同一只股票同一套策略在同一天只保留一条快照
        connection.execute(
            delete_sql,
            {
                "symbol": symbol,
                "strategy_name": strategy_name,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        connection.execute(insert_sql, records)

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
    insert_sql = text(
        """
        INSERT INTO backtest_run (
            symbol, strategy_name, parameters,
            annual_return, max_drawdown, sharpe_ratio, win_rate, turnover_rate
        ) VALUES (
            :symbol, :strategy_name, :parameters,
            :annual_return, :max_drawdown, :sharpe_ratio, :win_rate, :turnover_rate
        )
        """
    )
    with engine.begin() as connection:
        connection.execute(insert_sql, payload)
