### 1. 入口层

入口层就是 `cli.py`

它只负责两件事

- 接命令
- 把命令转交给总流程

### 2. 编排层

编排层主要是 `services/pipeline.py`

总调度器

比如一次单股回测，它会决定

1. 先读哪只股票的数据
2. 再调用哪个策略
3. 信号要不要先落库
4. 回测结果怎么算
5. 图表和报告怎么保存

也就是说
它不负责具体算法细节
但它负责把每一层按顺序串起来

### 3. 领域层

这层是项目真正干活的功能模块

#### `data/`

这一层做 3 件事

- 抓数据
- 清洗数据
- 读写数据

把这三个动作拆开，是因为它们以后容易变化

比如

- 换数据源，只动 `fetcher.py`
- 改字段规则，只动 `cleaning.py`
- 改数据库读写方式，只动 `repository.py`

这里我最后把 `repository.py` 定成了原生 SQL 写法

也就是它现在主要做的是

- 把 DataFrame 转成适合批量写库的记录
- 直接写 `SELECT` `INSERT` `DELETE` 这种 SQL 文本
- 通过参数绑定把 Python 变量传给数据库

这样仓库层的边界就很清楚
它就是一层很直接的数据访问封装
不是 ORM 实体仓库

#### `strategies/`

策略层只做一件事

从行情表生成 `signal`

也就是说
它不管数据库
也不管图表
更不管回测绩效

#### `backtest/`

回测层负责把信号变成结果

拆成了两部分

- `engine.py` 做单标的
- `portfolio.py` 做组合层

单标的那层主要是

- 持仓怎么滞后
- 成本怎么算
- 净值怎么算
- 交易记录怎么抽出来

组合层主要是

- 多只股票怎么对齐到同一个时间轴
- 怎么把单标的结果汇总成组合结果

#### `risk/`

风控单独拆了一层
而不是直接塞进策略里

策略说的是“我想怎么做”
风控说的是“我最终能不能这么做”

#### `visualization/`

这层只画图

不把画图逻辑混到回测里
一旦图表需求变了，回测本身不应该跟着改

#### `execution/`

这层目前只是模拟执行

把最后一条信号翻译成人能看懂的话

比如

- BUY
- SELL
- HOLD
- WAIT

### 4. 基础设施层

这层主要是 `config/` 和 `db/`

#### `config/`

我把配置统一收口到 `Settings`
这样所有模块都不用自己去到处读环境变量

#### `db/`

数据库这层负责两件事

- 定义表结构
- 建立数据库连接

这里我明确选的是 `SQLAlchemy Core` 而不是 ORM

也就是

- `base.py` 里放 `MetaData`
- `models.py` 里放 `Table(...)`
- `session.py` 里只保留 `engine` 和 `init_db`
- 不维护 ORM class
- 不维护 `sessionmaker`
- 不做对象状态同步

也就是说

- 表结构定义这一层是 Core
- 真正操作数据库的仓库层是原生 SQL

这么拆的好处是

- 表结构集中管理
- 读写逻辑直接对应真实 SQL
- 项目里每次查库和写库到底做了什么更容易讲清楚
- SQLite 切 MySQL 时不需要改上层业务逻辑

以后不管是 SQLite 切 MySQL
还是加新表
都有一个固定位置能找到

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

每一步都能单独讲
也能单独替换

## 为什么保留 SQLite 和 MySQL 两种选择

- SQLite 适合第一次跑通
- MySQL 更像实际项目环境

第一次用 SQLite
因为这样几乎没有环境门槛

如果要转真实项目
再切 MySQL 就行

底层这一层我已经尽量做成数据库无关的结构设计
所以切换数据库时，主要只是换连接字符串和初始化方式

## 如果后面继续扩展

我觉得最顺的扩展方向有 3 个

### 1. 横向扩策略

就是继续往 `strategies/` 里加新策略

这个项目目前的结构就是为了让这件事变简单

### 2. 纵向扩组合层

比如加

- 调仓日历
- 权重约束
- 行业约束
- 因子排序

### 3. 再往上包一层展示界面

比如做一个简单网页
或者做成 Streamlit 工具

这样整个项目会更完整
