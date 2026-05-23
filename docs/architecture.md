### 1. 入口层

`cli.py`

负责两件事

- 接命令
- 把命令转交给总流程

### 2. 编排层

编排层 `services/pipeline.py`

总调度器

比如一次单股回测，决定

1. 先读哪只股票的数据
2. 再调用哪个策略
3. 信号要不要先落库
4. 回测结果怎么算
5. 图表和报告怎么保存

负责把每一层按顺序串起来

### 3. 领域层

#### `data/`

- 抓数据
- 清洗数据
- 读写数据

解耦，便于后续修改

比如

- 换数据源，只动 `fetcher.py`
- 改字段规则，只动 `cleaning.py`
- 改数据库读写方式，只动 `repository.py`

#### `strategies/`

从行情表生成 `signal`

#### `backtest/`

负责信号变成结果

拆成两部分

- `engine.py` 做单标的
- `portfolio.py` 做组合层

单标的层

- 持仓怎么滞后
- 成本怎么算
- 净值怎么算
- 交易记录怎么抽出来

组合层

- 多只股票怎么对齐到同一个时间轴
- 怎么把单标的结果汇总成组合结果

#### `risk/`

策略输出“我想怎么做”
风控输出“我最终能不能这么做”

#### `visualization/`

根据回测结果画图

#### `execution/`

把最后一条信号翻译成人能看懂的话

比如

- BUY
- SELL
- HOLD
- WAIT

### 4. 基础设施层

`config/` 和 `db/`

#### `config/`

把配置统一收口到 `Settings`
所有模块都不用自己去读环境变量

#### `db/`

- 定义表结构
- 建立数据库连接

- `base.py` 里放 `MetaData`
- `models.py` 里放 `Table(...)`
- `session.py` 里只保留 `engine` 和 `init_db`

- 表结构定义这一层是 Core
- 真正操作数据库的仓库层是原生 SQL

## 一次完整回测在项目里是怎么流动的

执行一条单股回测命令

```bash
python -m ashare_backtest.cli backtest --symbol 600519 --strategy ma_cross
```

大概会这样走

1. CLI 先解析参数
2. Pipeline 决定整体流程
3. Repository 从数据库读历史日线
4. Strategy 生成 `signal`
5. Signal 先写入 `strategy_signal`
6. BacktestEngine 把 `signal` 变成持仓和净值
7. Risk 层对持仓做限制
8. Visualization 保存图表
9. Reporting 保存 JSON 和 CSV
10. Execution 生成最新模拟信号
11. 最后把摘要写进 `backtest_run`

每一步都能单独替换
