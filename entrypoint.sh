#!/bin/bash
set -e

# 如果设置了 ENV=test，则清空并重建表
if [ "$APP_ENV" = "test" ]; then
  echo "检测到测试环境，正在重置数据库结构..."
  python << END
import os
from sqlalchemy import create_engine, MetaData
from config.database import DATABASE_URL
# 1. 获取异步 URL

# 2. 将异步驱动 aiomysql 替换为同步驱动 pymysql
# 结果类似: mysql+pymysql://user:pass@host:port/db
sync_url = DATABASE_URL.replace("mysql+aiomysql://", "mysql+pymysql://")

try:
    # 使用同步驱动创建引擎
    engine = create_engine(sync_url)
    m = MetaData()
    m.reflect(bind=engine)
    m.drop_all(bind=engine)
    print("所有表已清空（包括 alembic_version）！")
except Exception as e:
    print(f"清空失败: {e}")
    exit(1)
END
fi

echo "执行迁移..."
alembic upgrade head

echo "启动程序..."
exec uvicorn main:app --host 0.0.0.0 --port 9000 --workers 1