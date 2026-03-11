from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db

router = APIRouter()


# 🔹列出所有表名
@router.get("/tables", summary="列出所有表名")
async def list_tables(db: AsyncSession = Depends(get_db)):
    sql = text("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")
    result = await db.execute(sql)
    tables = [row[0] for row in result.fetchall()]
    return {"tables": tables}


# 🔹查看某张表的所有数据（分页可选）
@router.get("/tables/{table_name}", summary="查看表的所有数据")
async def get_table_data(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # 用 information_schema 判断表存在
    sql_tables = text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
    )
    result_tables = await db.execute(sql_tables)
    tables = [row[0] for row in result_tables.fetchall()]

    if table_name not in tables:
        return JSONResponse(status_code=404, content={"error": f"Table '{table_name}' not found"})

    # 查表数据
    sql = text(f"SELECT * FROM `{table_name}` LIMIT :limit OFFSET :offset")
    result = await db.execute(sql, {"limit": limit, "offset": offset})
    rows = result.mappings().all()
    rows = [dict(row) for row in rows]  # 这里转换

    return {"table": table_name, "total_rows": len(rows), "data": rows}
