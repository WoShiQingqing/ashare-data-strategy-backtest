# 命令行入口

from __future__ import annotations

import argparse

from ashare_backtest.services import ASharePipeline
from ashare_backtest.strategies import build_strategy
from ashare_backtest.strategies.registry import strategy_choices


def _add_strategy_arguments(parser: argparse.ArgumentParser) -> None:
    # 给命令补充统一的策略参数
    # 每个策略不一定用得上所有参数
    # 真正会被消费哪些参数，由 registry 决定
    parser.add_argument(
        "--strategy",
        required=True,
        choices=strategy_choices(),
        help="策略名称",
    )
    parser.add_argument("--short-window", type=int, help="均线短周期")
    parser.add_argument("--long-window", type=int, help="均线长周期")
    parser.add_argument("--lookback", type=int, help="动量回看窗口")
    parser.add_argument("--threshold", type=float, help="动量阈值")
    parser.add_argument("--window", type=int, help="均值回归或布林带窗口")
    parser.add_argument("--entry-z", type=float, help="均值回归开仓 z-score")
    parser.add_argument("--exit-z", type=float, help="均值回归平仓 z-score")
    parser.add_argument("--num-std", type=float, help="布林带标准差倍数")


def _add_date_arguments(parser: argparse.ArgumentParser) -> None:
    # 给命令补充统一的日期参数
    parser.add_argument("--start", help="开始日期，例如 20200101")
    parser.add_argument("--end", help="结束日期，例如 20241231")


def _parse_symbols(args: argparse.Namespace, pipeline: ASharePipeline) -> list[str]:
    # 把 CLI 的 symbol 参数统一解析成列表
    # 这样后面的 fetch 和组合回测都能共用一套处理逻辑
    if getattr(args, "symbol", None):
        return [str(args.symbol).zfill(6)]
    if getattr(args, "symbols", None):
        return [item.strip().zfill(6) for item in args.symbols.split(",") if item.strip()]
    if getattr(args, "use_watchlist", False):
        return list(pipeline.settings.watchlist)
    raise ValueError("必须提供 --symbol、--symbols 或 --use-watchlist")


def _build_strategy_from_args(args: argparse.Namespace):
    # 根据 CLI 参数构建策略实例
    # 这里不直接 new 某个策略类，而是走注册表统一创建
    return build_strategy(
        args.strategy,
        short_window=getattr(args, "short_window", None),
        long_window=getattr(args, "long_window", None),
        lookback=getattr(args, "lookback", None),
        threshold=getattr(args, "threshold", None),
        window=getattr(args, "window", None),
        entry_z=getattr(args, "entry_z", None),
        exit_z=getattr(args, "exit_z", None),
        num_std=getattr(args, "num_std", None),
    )


def build_parser() -> argparse.ArgumentParser:
    # 构建命令行参数解析器
    # 这个函数只管定义命令，不执行任何业务逻辑
    parser = argparse.ArgumentParser(description="A 股抓取回测项目")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="初始化数据库表")
    subparsers.add_parser("list-symbols", help="列出数据库里已有的股票代码")

    fetch_parser = subparsers.add_parser("fetch", help="抓取并存储日线数据")
    fetch_group = fetch_parser.add_mutually_exclusive_group(required=True)
    fetch_group.add_argument("--symbol", help="单只股票代码，例如 600519")
    fetch_group.add_argument("--symbols", help="多个股票代码，逗号分隔")
    fetch_group.add_argument("--use-watchlist", action="store_true", help="抓取 .env 中 WATCHLIST")
    _add_date_arguments(fetch_parser)
    fetch_parser.add_argument("--adjust", default="qfq", help="复权方式，例如 qfq / hfq / 空字符串")

    backtest_parser = subparsers.add_parser("backtest", help="运行单标的策略回测")
    backtest_parser.add_argument("--symbol", required=True, help="股票代码，例如 600519")
    _add_date_arguments(backtest_parser)
    _add_strategy_arguments(backtest_parser)

    portfolio_parser = subparsers.add_parser("backtest-portfolio", help="运行股票池组合回测")
    portfolio_group = portfolio_parser.add_mutually_exclusive_group(required=True)
    portfolio_group.add_argument("--symbols", help="多个股票代码，逗号分隔")
    portfolio_group.add_argument("--use-watchlist", action="store_true", help="使用 .env 中 WATCHLIST")
    _add_date_arguments(portfolio_parser)
    _add_strategy_arguments(portfolio_parser)
    portfolio_parser.add_argument("--portfolio-name", default="watchlist", help="组合名称")

    paper_parser = subparsers.add_parser("paper", help="输出最新模拟交易信号")
    paper_parser.add_argument("--symbol", required=True, help="股票代码，例如 600519")
    _add_date_arguments(paper_parser)
    _add_strategy_arguments(paper_parser)

    return parser


def main() -> None:
    # CLI 主入口
    # 真正干活的还是 pipeline
    parser = build_parser()
    args = parser.parse_args()
    pipeline = ASharePipeline()

    if args.command == "init-db":
        pipeline.bootstrap()
        print("数据库表初始化完成")
        return

    if args.command == "list-symbols":
        symbols = pipeline.list_symbols()
        print("已入库股票:")
        for symbol in symbols:
            print(symbol)
        return

    if args.command == "fetch":
        pipeline.bootstrap()
        symbols = _parse_symbols(args, pipeline)
        results, errors = pipeline.fetch_many(
            symbols=symbols,
            start_date=args.start,
            end_date=args.end,
            adjust=args.adjust,
        )
        print("抓取并入库完成:")
        for symbol, rows in results.items():
            print(f"{symbol}: {rows}")
        if errors:
            print("以下股票抓取失败:")
            for symbol, message in errors.items():
                print(f"{symbol}: {message}")
        return

    if args.command == "backtest":
        strategy = _build_strategy_from_args(args)
        result, latest_signal, report_paths = pipeline.backtest(
            symbol=args.symbol,
            strategy=strategy,
            start_date=args.start,
            end_date=args.end,
        )
        print(f"回测完成: {str(args.symbol).zfill(6)} - {strategy.name}")
        for key, value in result.metrics.items():
            print(f"{key}: {value:.4f}")
        print(f"图表输出: {report_paths['chart']}")
        print(f"报告摘要: {report_paths['summary']}")
        print(f"交易明细: {report_paths['trades']}")
        print(f"最新信号: {latest_signal.action}, target_position={latest_signal.target_position:.2f}")
        return

    if args.command == "backtest-portfolio":
        strategy = _build_strategy_from_args(args)
        symbols = _parse_symbols(args, pipeline)
        result, report_paths = pipeline.backtest_portfolio(
            symbols=symbols,
            strategy=strategy,
            start_date=args.start,
            end_date=args.end,
            portfolio_name=args.portfolio_name,
        )
        print(f"组合回测完成: {args.portfolio_name} - {strategy.name}")
        print(f"symbols: {','.join(symbols)}")
        for key, value in result.metrics.items():
            print(f"{key}: {value:.4f}")
        print(f"组合图表: {report_paths['chart']}")
        print(f"报告摘要: {report_paths['summary']}")
        print(f"组合日度结果: {report_paths['daily']}")
        return

    if args.command == "paper":
        strategy = _build_strategy_from_args(args)
        _, latest_signal, report_paths = pipeline.backtest(
            symbol=args.symbol,
            strategy=strategy,
            start_date=args.start,
            end_date=args.end,
        )
        print(f"最新模拟信号: {latest_signal.action}")
        print(f"trade_date: {latest_signal.trade_date}")
        print(f"target_position: {latest_signal.target_position:.2f}")
        print(f"reason: {latest_signal.reason}")
        print(f"signal_file: {report_paths['signal']}")


if __name__ == "__main__":
    main()
