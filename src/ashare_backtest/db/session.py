# 数据库连接和建表入口

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from ashare_backtest.config import get_settings

from .base import Base


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
    # 返回 session 工厂，方便后续需要 ORM session 时复用
    # 这版项目大多直接用 engine + SQL
    # 但把 session 工厂留下，后续扩展 ORM 写法会更方便
    return sessionmaker(bind=engine or get_engine(), autoflush=False, autocommit=False)


def init_db(engine: Engine | None = None) -> Engine:
    # 根据 ORM 模型初始化数据库表
    # 第一次跑项目时，CLI 会先调用这里建表
    active_engine = engine or get_engine()
    Base.metadata.create_all(bind=active_engine)
    return active_engine
