# 数据库连接和建表入口
# 虽然项目已经把表结构切到了 Core
# 但上层依然统一从这里拿 engine 和初始化数据库

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from ashare_backtest.config import get_settings

from .base import metadata


def get_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    # 创建 SQLAlchemy engine
    # 其他模块不直接 create_engine，统一从这里取
    settings = get_settings()
    if settings.db_backend == "sqlite":
        # SQLite 使用本地文件
        # 所以要先把上级目录准备好
        settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(database_url or settings.database_url, echo=echo, future=True)


def get_session_factory(engine: Engine | None = None) -> sessionmaker:
    # 这个函数先保留，主要是为了兼容现有接口
    # 当前项目主体其实已经不依赖 ORM session
    return sessionmaker(bind=engine or get_engine(), autoflush=False, autocommit=False)


def init_db(engine: Engine | None = None) -> Engine:
    # 根据 Core 表结构初始化数据库表
    active_engine = engine or get_engine()
    metadata.create_all(bind=active_engine)
    return active_engine
