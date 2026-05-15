# 这个文件不再放 ORM 的 DeclarativeBase
# 改成直接放 SQLAlchemy Core 用的 MetaData
# 这样数据库层的表结构定义就是纯 Core 风格

from sqlalchemy import MetaData


# 统一的命名规则能让约束名更稳定
# 后面切 MySQL 或做迁移时也更容易读
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)
