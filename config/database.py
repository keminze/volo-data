import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = (
    f"mysql+aiomysql://{os.environ.get('MYSQL_USER')}:{os.environ.get('MYSQL_PASSWORD')}"
    + f"@{os.environ.get('MYSQL_HOST')}:{os.environ.get('MYSQL_PORT')}/{os.environ.get('MYSQL_DB')}?charset=utf8mb4"
)  # 存储连接信息的元数据库

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


async def get_db():
    async with async_session() as session:
        yield session


# 初始化数据库（异步）
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def del_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def del_single_table(table_name: str):
    """
    删除指定的某一个数据表
    :param table_name: 数据库中的表名字符串
    """
    async with engine.begin() as conn:
        # 1. 检查表是否存在于当前的 Base 映射中
        target_table = Base.metadata.tables.get(table_name)

        if target_table is not None:
            # 2. 仅删除指定的表对象
            # drop_all 接收一个 tables 参数，类型为 List[Table]
            await conn.run_sync(
                lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=[target_table])
            )
            print(f"成功删除表: {table_name}")
        else:
            print(f"未在 Metadata 中找到表: {table_name}，请检查")
