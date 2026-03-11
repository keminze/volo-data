import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 1. 导入你的配置和模型
from config.database import DATABASE_URL, Base
from config.models import *

# Alembic Config 对象
config = context.config

# 2. 注入你的 DATABASE_URL
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# 3. 设置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 4. 关键：指向你的模型元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """脱机模式"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """同步环境下的迁移执行"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步模式下的引擎创建和连接"""
    # 从配置中读取注入后的 URL 创建引擎
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式：判断当前是否有正在运行的 loop"""
    try:
        # 尝试获取当前的事件循环
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 如果在 FastAPI 等运行环境中，创建一个任务
        loop.create_task(run_async_migrations())
    else:
        # 如果在命令行执行（最常见情况），开启新循环
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
