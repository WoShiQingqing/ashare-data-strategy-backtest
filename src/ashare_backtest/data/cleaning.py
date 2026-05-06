# 这个文件负责把外部数据源返回的原始表
# 转成项目内部统一使用的日线格式
from __future__ import annotations

import pandas as pd


COLUMN_MAPPING = {
    # AkShare 返回的是中文列名
    # 这里统一映射成项目内部约定的英文列名
    "日期": "trade_date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_change",
    "涨跌额": "price_change",
    "换手率": "turnover_rate",
}

OUTPUT_COLUMNS = [
    # 输出字段顺序固定下来后
    # 后续写库、回测、导出报告会更稳定
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


def standardize_ashare_daily(raw_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    # 这是数据进入项目后的第一道整理工序
    # 这里做完以后，后面的模块都假设字段已经规范
    if raw_df.empty:
        raise ValueError(f"{symbol} 没有抓到任何数据")

    # 第一步先做列名映射
    df = raw_df.rename(columns=COLUMN_MAPPING).copy()
    required_columns = {"trade_date", "open", "high", "low", "close", "volume", "amount"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"原始数据缺少字段: {sorted(missing)}")

    df["symbol"] = str(symbol).zfill(6)
    df["source"] = "akshare"
    # 统一转成 date
    # 数据库里日线表按日期保存，不保留时分秒
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

    numeric_columns = [
        # 这些字段后面都要参与计算
        # 所以必须强制转成数值类型
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
    ]
    for column in numeric_columns:
        if column not in df.columns:
            # 某些数据源偶尔会缺少列
            # 这里先补默认值，避免后续逻辑直接报错
            df[column] = 0.0
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # 时间序列类项目最怕乱序和重复日期
    # 所以这里固定先排序再去重
    df = df.sort_values("trade_date").drop_duplicates(subset=["trade_date"]).reset_index(drop=True)
    df = df.dropna(subset=["close"])
    for column in ["open", "high", "low"]:
        # 开高低价偶尔会缺失
        # 这里用收盘价兜底，让最基础的策略还能跑
        df[column] = df[column].fillna(df["close"])

    # 量价类字段统一补默认值
    df["volume"] = df["volume"].fillna(0.0)
    df["amount"] = df["amount"].fillna(0.0)
    df["turnover_rate"] = df["turnover_rate"].fillna(0.0)

    # 如果源数据没给涨跌幅和涨跌额
    # 就根据收盘价自己补算
    df["pct_change"] = df["pct_change"].fillna(df["close"].pct_change().mul(100.0))
    df["price_change"] = df["price_change"].fillna(df["close"].diff())
    df["amplitude"] = df["amplitude"].fillna(0.0)

    # 最后只保留项目真正会用到的字段
    return df[OUTPUT_COLUMNS]
