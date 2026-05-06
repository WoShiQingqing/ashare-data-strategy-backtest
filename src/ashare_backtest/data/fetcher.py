# 这个文件只做一件事
# 从外部数据源抓原始日线表
from __future__ import annotations

import time

import pandas as pd

class AkshareAStockFetcher:
    # 当前项目默认通过 AkShare 抓 A 股日线
    # 以后如果切别的数据源，可以新写一个 fetcher 保持同样接口

    source = "akshare"

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        # A 股代码统一按 6 位处理
        # 这样数据库和命令行不会混用 1 位、4 位、6 位格式
        return str(symbol).zfill(6)

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
        max_retries: int = 3,
        retry_sleep: float = 1.0,
    ) -> pd.DataFrame:
        # 这里只负责拿原始数据
        # 不在这里做清洗，清洗统一交给 cleaning.py
        try:
            import akshare as ak
        except ImportError as exc:  # pragma: no cover
            raise ImportError("未安装 akshare，请先执行: pip install \".[dev]\"") from exc

        normalized = self.normalize_symbol(symbol)
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                # 如果数据源正常返回，这里直接把原始表交出去
                return ak.stock_zh_a_hist(
                    symbol=normalized,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
            except Exception as exc:  # pragma: no cover
                last_error = exc
                if attempt == max_retries:
                    break
                # 上游接口偶尔会断开连接
                # 简单 sleep 一下再重试，对批量抓取更稳
                time.sleep(retry_sleep)

        raise RuntimeError(f"{normalized} 抓取失败: {last_error}") from last_error
