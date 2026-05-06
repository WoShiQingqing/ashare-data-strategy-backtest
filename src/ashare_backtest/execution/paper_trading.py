# 模拟执行信号生成

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass
class PaperTradeSignal:
    # 模拟交易信号的数据结构
    # 这个对象最后会直接保存成 JSON 文件

    symbol: str
    strategy_name: str
    trade_date: str
    action: str
    target_position: float
    reason: str


class PaperTradingEngine:
    # 把策略最后一行结果翻译成可读的交易动作
    # 它不负责回测，只负责解释当前信号

    def generate_latest_signal(
        self,
        strategy_frame: pd.DataFrame,
        symbol: str,
        strategy_name: str,
    ) -> PaperTradeSignal:
        # 根据最新两期信号判断 BUY / SELL / HOLD / WAIT
        if strategy_frame.empty:
            raise ValueError("无法从空数据生成模拟信号")

        latest = strategy_frame.iloc[-1]
        previous_signal = (
            float(strategy_frame.iloc[-2]["signal"])
            if len(strategy_frame) > 1
            else 0.0
        )
        current_signal = float(latest["signal"])

        # 通过当前值和前一日值的关系，判断到底是买入还是继续持有
        if current_signal > previous_signal:
            action = "BUY"
            reason = "策略由空仓信号切换为持仓信号"
        elif current_signal < previous_signal:
            action = "SELL"
            reason = "策略由持仓信号切换为空仓信号"
        elif current_signal > 0:
            action = "HOLD"
            reason = "策略继续维持持仓"
        else:
            action = "WAIT"
            reason = "策略当前没有开仓信号"

        trade_date = pd.to_datetime(latest["trade_date"]).strftime("%Y-%m-%d")
        return PaperTradeSignal(
            symbol=str(symbol).zfill(6),
            strategy_name=strategy_name,
            trade_date=trade_date,
            action=action,
            target_position=current_signal,
            reason=reason,
        )

    def save_signal(self, signal: PaperTradeSignal, output_dir: Path | str = "output/signals") -> Path:
        # 把最新信号保存成 JSON 文件
        # 这样即使不懂 Python，也能直接打开文件看结果
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{signal.symbol}_{signal.strategy_name}_signal.json"
        path.write_text(json.dumps(asdict(signal), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
