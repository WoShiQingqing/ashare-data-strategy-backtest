# 数据库连接和建表入口
# 这里统一负责创建 engine 和初始化表结构
# 既然项目已经决定全面使用 SQLAlchemy Core
# 这一层就不再暴露 ORM session 相关接口

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ashare_backtest.config import get_settings

from .base import metadata


def get_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    # 创建 SQLAlchemy engine
    # 其他模块不直接 create_engine
    # 统一从这里拿连接入口
    settings = get_settings()
    if settings.db_backend == "sqlite":
        # SQLite 使用本地文件
        # 所以要先确保数据库目录存在
        settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(database_url or settings.database_url, echo=echo, future=True)


def init_db(engine: Engine | None = None) -> Engine:
    # 按照 Core Table 定义创建数据库表
    # 这里不会触发任何 ORM 映射行为
    active_engine = engine or get_engine()
    metadata.create_all(bind=active_engine)
    return active_engine
