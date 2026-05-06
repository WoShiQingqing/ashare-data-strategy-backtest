# A股抓取回测

## 这个项目现在能做什么

1. 抓 A 股日线
2. 把日线存到 SQLite 或 MySQL
3. 统一清洗字段和日期
4. 跑 4 个基础策略
5. 做单标的回测
6. 做股票池组合回测
7. 做基础风控
8. 生成图表
9. 导出 JSON 和 CSV 报告
10. 输出最新模拟信号

当前内置策略有

- `ma_cross`
- `momentum`
- `mean_reversion`
- `bollinger_band`

## 怎么拆项目结构

```text
A股抓取回测/
├── menu.sh
├── README.md
├── docs/
│   └── architecture.md
├── sql/
│   └── init_mysql.sql
├── src/
│   └── ashare_backtest/
│       ├── cli.py
│       ├── config/
│       ├── data/
│       ├── db/
│       ├── strategies/
│       ├── backtest/
│       ├── risk/
│       ├── visualization/
│       ├── execution/
│       └── services/
└── tests/
```

- `config` 是配置入口
- `data` 是抓数和读写数据
- `db` 是数据库表和连接
- `strategies` 是信号逻辑
- `backtest` 是收益和净值怎么算
- `risk` 是风控
- `visualization` 是画图
- `execution` 是模拟信号
- `services` 是把上面这些串起来
- `cli.py` 是命令行入口

## 环境要求

统一切到Python 3.11

- Python `3.11`
- SQLite 或 MySQL
- 默认数据源是 AkShare

## 最省事的启动方式

如果不想记命令，直接用菜单脚本就行

```bash
bash menu.sh
```

它会给一个中文菜单
像下面这些操作都可以直接选编号

- 创建虚拟环境
- 安装依赖
- 初始化数据库
- 抓取股票
- 跑单股回测
- 跑组合回测
- 生成模拟信号
- 跑测试

## 如果想手动跑命令

### 1. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 2. 准备配置文件

```bash
cp .env.example .env
```

默认配的是 SQLite
如果只是先跑通项目，直接用这个最省事

### 3. 初始化数据库表

```bash
PYTHONPATH=src MPLBACKEND=Agg MPLCONFIGDIR=output/matplotlib \
python -m ashare_backtest.cli init-db
```

### 4. 抓一只股票

```bash
PYTHONPATH=src MPLBACKEND=Agg MPLCONFIGDIR=output/matplotlib \
python -m ashare_backtest.cli fetch --symbol 600519 --start 20200101 --end 20241231
```

### 5. 跑一次单股回测

```bash
PYTHONPATH=src MPLBACKEND=Agg MPLCONFIGDIR=output/matplotlib \
python -m ashare_backtest.cli backtest --symbol 600519 --strategy ma_cross --short-window 5 --long-window 20
```

### 6. 跑一次组合回测

```bash
PYTHONPATH=src MPLBACKEND=Agg MPLCONFIGDIR=output/matplotlib \
python -m ashare_backtest.cli backtest-portfolio --symbols 600519,000001 --strategy momentum --lookback 10 --threshold 0.01 --portfolio-name demo_pool
```

### 7. 生成最新模拟信号

```bash
PYTHONPATH=src MPLBACKEND=Agg MPLCONFIGDIR=output/matplotlib \
python -m ashare_backtest.cli paper --symbol 600519 --strategy mean_reversion --window 20 --entry-z 1.5 --exit-z 0.5
```

## 如果想切 MySQL

只需要改 `.env`

```bash
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=ashare_backtest
```

然后先执行

```bash
mysql -u root -p < sql/init_mysql.sql
```

再跑一次

```bash
PYTHONPATH=src python -m ashare_backtest.cli init-db
```

业务代码本身不用改

## 输出结果都在哪

- `output/ashare.db`
- `output/plots/`
- `output/signals/`
- `output/reports/`

这些目录我默认不会 git 进仓库
因为它们本质上是运行产物，不是源码

如果只是想让别人快速知道跑完以后大概会产出什么
我更倾向于保留一个很小的样例目录

- `examples/sample_outputs/`

数据库里还会存两类很有用的业务结果

- `strategy_signal`
- `backtest_run`

可以回头查某次实验到底用了什么参数、给过什么信号

## 如果继续往下做

大概率会优先做这些

1. 因子排序和定期调仓
2. 更合理的组合约束
3. 参数搜索
4. Web 页面
5. 更完整的实验记录

## 还有一份架构说明

看怎么拆模块的
可以看这份

- [架构说明](docs/architecture.md)
