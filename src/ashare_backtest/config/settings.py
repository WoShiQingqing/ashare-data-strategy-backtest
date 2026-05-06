# 项目配置读取与统一出口

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

try:
    # dotenv 是可选依赖
    # 装了就自动读取 .env，没装也不影响最基础的解释器导入
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> bool:
        return False


# 模块导入时就尝试加载 .env
# 这样后面的 Settings 直接读环境变量即可
load_dotenv()


def _split_csv(value: str) -> list[str]:
    # 把逗号分隔的环境变量解析成列表
    # WATCHLIST 这种字段会走这里
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # 集中管理项目运行参数，避免各模块直接读环境变量
    # dataclass 的好处是字段一眼能看全，调试时也容易打印

    # 项目级基础信息
    project_name: str = os.getenv("PROJECT_NAME", "A股抓取回测")
    environment: str = os.getenv("ENV", "dev")
    market: str = os.getenv("MARKET", "CN_A")

    # 数据库后端配置
    db_backend: str = os.getenv("DB_BACKEND", "sqlite").lower()
    sqlite_path: Path = Path(os.getenv("SQLITE_PATH", "output/ashare.db"))
    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "change_me")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "ashare_backtest")

    # 默认股票池配置
    watchlist: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            _split_csv(os.getenv("WATCHLIST", "000001,600519,601318"))
        )
    )

    # 默认抓取区间和回测交易成本
    default_start_date: str = os.getenv("DEFAULT_START_DATE", "20180101")
    default_end_date: str = os.getenv("DEFAULT_END_DATE", "20251231")
    default_adjust: str = os.getenv("DEFAULT_ADJUST", "qfq")
    fee_rate: float = float(os.getenv("FEE_RATE", "0.0005"))
    slippage_rate: float = float(os.getenv("SLIPPAGE_RATE", "0.0002"))

    @property
    def database_url(self) -> str:
        # 根据当前后端类型统一生成 SQLAlchemy 连接串
        # 这样数据库切换只改配置，不改业务代码
        if self.db_backend == "mysql":
            return (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
                "?charset=utf8mb4"
            )

        # 默认走 SQLite，方便第一次上手直接运行
        return f"sqlite:///{self.sqlite_path.as_posix()}"

    @property
    def plot_dir(self) -> Path:
        # 统一图表输出目录
        return Path("output/plots")

    @property
    def signal_dir(self) -> Path:
        # 统一模拟信号输出目录
        return Path("output/signals")

    @property
    def report_dir(self) -> Path:
        # 统一回测报告输出目录
        return Path("output/reports")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # 缓存配置对象，避免在一次进程内重复解析
    # 一个进程里配置通常不会变，缓存能减少重复构造
    return Settings()
