# 项目主编排流程

from __future__ import annotations

from ashare_backtest.backtest import (
    BacktestEngine,
    BacktestResult,
    PortfolioBacktestEngine,
    PortfolioBacktestResult,
)
from ashare_backtest.config import Settings, get_settings
from ashare_backtest.data import (
    AkshareAStockFetcher,
    list_available_symbols,
    load_daily_bars,
    load_many_daily_bars,
    save_backtest_run,
    standardize_ashare_daily,
    upsert_daily_bars,
    upsert_strategy_signals,
)
from ashare_backtest.db import get_engine, init_db
from ashare_backtest.execution import PaperTradeSignal, PaperTradingEngine
from ashare_backtest.strategies import BaseStrategy
from ashare_backtest.services.reporting import ReportWriter


class ASharePipeline:
    # 串联抓取、清洗、回测、出图、落库、出报告的总调度器
    # 你可以把它理解成项目的总流程控制器

    def __init__(self, settings: Settings | None = None) -> None:
        # 初始化时把各层依赖都装配好
        # 后面的 CLI 只需要和这个对象打交道
        self.settings = settings or get_settings()
        self.engine = get_engine()
        self.fetcher = AkshareAStockFetcher()
        self.plotter = None
        self.paper_trading = PaperTradingEngine()
        self.backtest_engine = BacktestEngine()
        self.portfolio_engine = PortfolioBacktestEngine()
        self.report_writer = ReportWriter(self.settings.report_dir)

    def _get_plotter(self):
        # 懒加载绘图器，避免纯数据库命令也导入matplotlib
        if self.plotter is None:
            from ashare_backtest.visualization import BacktestPlotter

            self.plotter = BacktestPlotter(self.settings.plot_dir)
        return self.plotter

    def bootstrap(self) -> None:
        # 初始化数据库表
        init_db(self.engine)

    def fetch_and_store(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str | None = None,
    ) -> int:
        # 抓取单只股票并入库
        # 这个函数把抓取和清洗串在一起
        # 所以上层调用时不需要自己再分两步写
        start = start_date or self.settings.default_start_date
        end = end_date or self.settings.default_end_date
        adjust_mode = adjust or self.settings.default_adjust

        raw_df = self.fetcher.fetch_daily_bars(
            symbol=symbol,
            start_date=start,
            end_date=end,
            adjust=adjust_mode,
        )
        cleaned_df = standardize_ashare_daily(raw_df, symbol)
        return upsert_daily_bars(cleaned_df, self.engine)

    def fetch_many(
        self,
        symbols: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str | None = None,
    ) -> tuple[dict[str, int], dict[str, str]]:
        # 批量抓取多只股票，并把失败项单独返回
        # 这样批量任务里某一只失败，不会影响其他股票继续入库
        results: dict[str, int] = {}
        errors: dict[str, str] = {}
        for symbol in symbols:
            normalized = str(symbol).zfill(6)
            try:
                results[normalized] = self.fetch_and_store(
                    symbol=normalized,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
            except Exception as exc:
                errors[normalized] = str(exc)
        return results, errors

    def list_symbols(self) -> list[str]:
        # 列出当前数据库中的股票代码
        return list_available_symbols(self.engine)

    def build_strategy_frame(
        self,
        symbol: str,
        strategy: BaseStrategy,
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        # 构建策略信号表，并顺手把信号快照存入数据库
        # 这一步是抓数和回测之间最关键的桥梁
        bars = load_daily_bars(symbol=symbol, engine=self.engine, start_date=start_date, end_date=end_date)
        if bars.empty:
            raise ValueError(f"{symbol} 在数据库中没有数据，请先执行 fetch")
        strategy_frame = strategy.generate_signals(bars)
        strategy_frame["symbol"] = str(symbol).zfill(6)
        # 信号先落库，再进入回测
        # 以后想单独分析策略行为时，可以直接查 strategy_signal 表
        upsert_strategy_signals(
            strategy_frame.loc[:, ["symbol", "strategy_name", "trade_date", "signal", "score"]],
            self.engine,
        )
        return strategy_frame

    def backtest(
        self,
        symbol: str,
        strategy: BaseStrategy,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[BacktestResult, PaperTradeSignal, dict[str, str]]:
        # 运行单标的完整回测流程
        # 这是项目里最常用的一条主链路
        strategy_frame = self.build_strategy_frame(
            symbol=symbol,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
        )
        result = self.backtest_engine.run(
            strategy_frame=strategy_frame,
            fee_rate=self.settings.fee_rate,
            slippage_rate=self.settings.slippage_rate,
        )
        normalized_symbol = str(symbol).zfill(6)
        chart_path = self._get_plotter().plot(
            result.result_frame,
            symbol=normalized_symbol,
            strategy_name=strategy.name,
        )
        latest_signal = self.paper_trading.generate_latest_signal(
            strategy_frame=strategy_frame,
            symbol=symbol,
            strategy_name=strategy.name,
        )
        signal_path = self.paper_trading.save_signal(latest_signal, self.settings.signal_dir)
        # 报告和信号文件既是用户输出，也是后续回看实验的凭证
        report_paths = self.report_writer.save_single_backtest(
            symbol=normalized_symbol,
            strategy_name=strategy.name,
            metrics=result.metrics,
            result_frame=result.result_frame,
            trades=result.trades,
            extra={
                "chart_path": str(chart_path),
                "signal_path": str(signal_path), 
                "strategy_parameters": strategy.parameters,
            },
        )
        save_backtest_run(
            # 这里把运行参数也一起写进数据库
            # 方便以后回看“这组指标到底是怎么跑出来的”
            engine=self.engine,
            symbol=normalized_symbol,
            strategy_name=strategy.name,
            parameters={
                "mode": "single",
                "start_date": start_date,
                "end_date": end_date,
                "strategy_parameters": strategy.parameters,
                "report_paths": report_paths,
                "chart_path": str(chart_path),
                "signal_path": str(signal_path),
            },
            metrics=result.metrics,
        )
        report_paths["chart"] = str(chart_path)
        report_paths["signal"] = str(signal_path)
        return result, latest_signal, report_paths

    def backtest_portfolio(
        self,
        symbols: list[str],
        strategy: BaseStrategy,
        start_date: str | None = None,
        end_date: str | None = None,
        portfolio_name: str = "watchlist",
    ) -> tuple[PortfolioBacktestResult, dict[str, str]]:
        # 运行股票池组合回测流程
        # 组合回测会逐只股票先生成信号，再汇总成组合净值
        normalized_symbols = [str(symbol).zfill(6) for symbol in symbols]
        bars_map = load_many_daily_bars(
            symbols=normalized_symbols,
            engine=self.engine,
            start_date=start_date,
            end_date=end_date,
        )

        constituent_results = {}
        for symbol, bars in bars_map.items():
            if bars.empty:
                # 批量场景下允许个别股票没有数据，跳过即可
                continue
            # 组合里每只股票先按单标的方式生成策略信号
            strategy_frame = strategy.generate_signals(bars)
            strategy_frame["symbol"] = symbol
            upsert_strategy_signals(
                strategy_frame.loc[:, ["symbol", "strategy_name", "trade_date", "signal", "score"]],
                self.engine,
            )
            constituent_results[symbol] = self.backtest_engine.run(
                strategy_frame=strategy_frame,
                fee_rate=self.settings.fee_rate,
                slippage_rate=self.settings.slippage_rate,
            ).result_frame

        portfolio_result = self.portfolio_engine.run(
            constituent_frames=constituent_results,
            fee_rate=self.settings.fee_rate,
            slippage_rate=self.settings.slippage_rate,
        )
        chart_path = self._get_plotter().plot_portfolio(
            portfolio_result.portfolio_frame,
            portfolio_name=portfolio_name,
            strategy_name=strategy.name,
        )
        report_paths = self.report_writer.save_portfolio_backtest(
            portfolio_name=portfolio_name,
            strategy_name=strategy.name,
            metrics=portfolio_result.metrics,
            portfolio_frame=portfolio_result.portfolio_frame,
            constituents=portfolio_result.constituent_frames,
            extra={
                "start_date": start_date,
                "end_date": end_date,
                "strategy_parameters": strategy.parameters,
                "chart_path": str(chart_path),
            },
        )
        save_backtest_run(
            # 组合层也落一份摘要
            # symbol 这里固定写 PORTFOLIO，表示它不是某一只股票
            engine=self.engine,
            symbol="PORTFOLIO",
            strategy_name=strategy.name,
            parameters={
                "mode": "portfolio",
                "portfolio_name": portfolio_name,
                "symbols": normalized_symbols,
                "start_date": start_date,
                "end_date": end_date,
                "strategy_parameters": strategy.parameters,
                "report_paths": report_paths,
                "chart_path": str(chart_path),
            },
            metrics=portfolio_result.metrics,
        )
        report_paths["chart"] = str(chart_path)
        return portfolio_result, report_paths
