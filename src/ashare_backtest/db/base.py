# 这个 Base 是所有 ORM 模型的根
# 后面的 StockDailyBar 和 StrategySignal 都继承它
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # 这里不放公共字段
    # 目前只把它当成 SQLAlchemy 的声明式基类
    pass
