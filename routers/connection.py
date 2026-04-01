import os
import uuid

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from config.logging_config import logger
from config.models import DBConnection
from config.parameter import DBConnectRequest, UpdateDBConnectRequest
from dependencies import get_current_user
from services.auth import User

# from services.auth import get_current_user_idconnection
from services.db import (
    csv_to_sqlite,
    delete_db_collections,
    excel_to_sqlite,
    get_db_tables,
    init_db_connection,
    test_db_connection,
)

router = APIRouter()

db_dir = "./uploaded_sqlite_dbs"
os.makedirs(db_dir, exist_ok=True)

temp_file_dir = "./tempfiles"
os.makedirs(temp_file_dir, exist_ok=True)


@router.post("/connect", summary="验证数据库可连接，获取数据库所有表")
async def connect_db(
    req: DBConnectRequest = Depends(DBConnectRequest.as_connect_request),
    #  req_user_id : int = Depends(get_current_user_id),
):
    # logger.info(f"Received connection request: {req.model_dump()}")
    try:
        try:
            if req.db_type == "sqlite":
                logger.info("尝试连接到 SQLite 数据库")
                sqlite_url = req.db_url
                if not req.db_url and not req.db_file:
                    return JSONResponse(
                        status_code=400, content="连接 sqlite 需要 db_url 或 db_file"
                    )
                if req.db_file:
                    db_file_path = os.path.join(db_dir, f"{uuid.uuid4()}_{req.db_file.filename}")
                    with open(db_file_path, "wb") as f:
                        f.write(await req.db_file.read())
                    sqlite_url = db_file_path
                    success, tables = await run_in_threadpool(
                        get_db_tables, req.db_type, path=sqlite_url
                    )
                    # if test_db_connection(req.db_type,path=sqlite_url):
                    if success:
                        logger.info(
                            f"Successfully connected to SQLite database at {sqlite_url}, tables: {tables}"
                        )
                        os.remove(sqlite_url)
                    else:
                        return JSONResponse(
                            status_code=400, content="无法连接到 SQLite 数据库，请检查文件是否有效"
                        )

            elif req.db_type == "mysql":
                logger.info("尝试连接到 MySQL 数据库")
                success, tables = await run_in_threadpool(
                    get_db_tables,
                    req.db_type,
                    host=req.host,
                    port=req.port,
                    user=req.user,
                    password=req.password,
                    database=req.dbname,
                )
                # if test_db_connection(req.db_type,host=req.host,port=req.port,user=req.user,password=req.password,database=req.dbname):
                if success:
                    logger.info(
                        f"Successfully connected to MySQL database at {req.host}:{req.port}/{req.dbname}, tables: {tables}"
                    )
                else:
                    return JSONResponse(
                        status_code=400, content="无法连接到 MySQL 数据库，请检查连接信息是否正确"
                    )

            elif req.db_type == "postgres":
                logger.info("尝试连接到 Postgres 数据库")
                success, tables = await run_in_threadpool(
                    get_db_tables,
                    req.db_type,
                    host=req.host,
                    port=req.port,
                    user=req.user,
                    password=req.password,
                    database=req.dbname,
                )
                # if test_db_connection(req.db_type,host=req.host,port=req.port,user=req.user,password=req.password,database=req.dbname):
                if success:
                    logger.info(
                        f"Successfully connected to Postgres database at {req.host}:{req.port}/{req.dbname}, tables: {tables}"
                    )
                else:
                    return JSONResponse(
                        status_code=400,
                        content="无法连接到 Postgres 数据库，请检查连接信息是否正确",
                    )

            elif req.db_type == "oracle":
                logger.info("尝试连接到 Oracle 数据库")
                success, tables = await run_in_threadpool(
                    get_db_tables,
                    req.db_type,
                    user=req.user,
                    password=req.password,
                    database=req.dsn,
                )
                # if test_db_connection(req.db_type,user=req.user,password=req.password,database=req.dsn):
                if success:
                    logger.info(
                        f"Successfully connected to Oracle database at {req.dsn}, tables: {tables}"
                    )
                else:
                    return JSONResponse(
                        status_code=400, content="无法连接到 Oracle 数据库，请检查连接信息是否正确"
                    )

            elif req.db_type == "duckdb":
                logger.info("尝试连接到 DuckDB")
                success, tables = await run_in_threadpool(
                    get_db_tables, req.db_type, path=req.db_url
                )
                # if test_db_connection(req.db_type,path=req.db_url):
                if success:
                    logger.info(
                        f"Successfully connected to DuckDB database at {req.db_url}, tables: {tables}"
                    )
                    # os.remove(sqlite_url)
                else:
                    return JSONResponse(
                        status_code=400, content="无法连接到 DuckDB 数据库，请检查连接信息是否正确"
                    )

            # elif req.db_type == "excel":
            #     logger.info(f"尝试解析 Excel")
            #     if not req.db_file:
            #         return JSONResponse(status_code=400, content="解析 Excel 需要 ecxcel文件")
            #     temp_file_path = os.path.join(temp_file_dir, f"{uuid.uuid4()}_{req.db_file.filename}")
            #     db_file_path = os.path.join(db_dir, f"{uuid.uuid4()}.sqlite")
            #     with open(temp_file_path, "wb") as f:
            #         f.write(await req.db_file.read())
            #     try:
            #         await run_in_threadpool(excel_to_sqlite,temp_file_path,db_file_path)
            #         try:
            #             os.remove(temp_file_path)
            #         except Exception as e:
            #             logger.error(f"Error deleting temp file: {str(e)}",exc_info=True)
            #     except Exception as e:
            #         logger.error(f"Error parsing Excel: {str(e)}",exc_info=True)
            #         return JSONResponse(status_code=400, content="无法解析 Excel 文件，请检查数据是否异常")

            # elif req.db_type == "csv":
            #     logger.info(f"尝试解析 CSV")
            #     if not req.db_file:
            #         return JSONResponse(status_code=400, content="解析 CSV 需要 csv文件")

            #     temp_file_path = os.path.join(temp_file_dir, f"{uuid.uuid4()}_{req.db_file.filename}")
            #     db_file_path = os.path.join(db_dir, f"{uuid.uuid4()}.sqlite")
            #     with open(temp_file_path, "wb") as f:
            #         f.write(await req.db_file.read())
            #     try:
            #         await run_in_threadpool(csv_to_sqlite,temp_file_path,db_file_path)
            #         try:
            #             os.remove(temp_file_path)
            #         except Exception as e:
            #             logger.error(f"Error deleting temp file: {str(e)}",exc_info=True)
            #     except Exception as e:
            #         logger.error(f"Error parsing CSV: {str(e)}",exc_info=True)
            #         return JSONResponse(status_code=400, content="无法解析 CSV 文件，请检查数据是否异常")

            # TODO: 添加更多数据源支持

            else:
                logger.error(f"不支持的数据源类型: {req.db_type}")
                return JSONResponse(status_code=400, content=f"不支持的数据源类型: {req.db_type}")

        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}", exc_info=True)
            return JSONResponse(status_code=400, content=f"无法连接到数据源，错误信息: {str(e)}")
        # 保存到 ORM
        # collection_prefix = str(uuid.uuid4())
        # conn_info = DBConnection(
        #     user_id=req.user_id,
        #     name=req.name,
        #     db_description=req.db_description,
        #     db_type=req.db_type,
        #     host=req.host,
        #     port=req.port,
        #     username=req.user,
        #     password=req.password,  # ⚠️ 建议加密存储
        #     database=req.dbname,
        #     db_url=req.db_url,
        #     db_file_path=db_file_path if req.db_type in ["sqlite","excel","csv"] and req.db_file else None,
        #     dsn=req.dsn,
        #     collection_prefix=collection_prefix
        # )
        # db.add(conn_info)
        # await db.commit()
        # await db.refresh(conn_info)
        # try:
        #     await run_in_threadpool(init_db_connection,conn_info,collection_prefix=conn_info.collection_prefix,db_type=conn_info.db_type)
        # except Exception as e:
        #     logger.error(f"Error initializing db connection: {str(e)}",exc_info=True)
        #     return JSONResponse(status_code=400, content=f"无法初始化数据库连接，错误信息: {str(e)}")

        return JSONResponse(content={"message": "connection successful", "tables": tables})

    except Exception as e:
        logger.error(f"Error connecting db: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content=f"连接失败，服务器内部错误: {str(e)}")


@router.post("/init", summary="初始化数据源，保存和训练数据源信息")
async def init_connection(
    req: DBConnectRequest = Depends(DBConnectRequest.as_form),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        try:
            if req.db_type == "sqlite":
                logger.info("尝试连接到 SQLite 数据库")
                sqlite_url = req.db_url
                if not req.db_url and not req.db_file:
                    return JSONResponse(
                        status_code=400, content="连接 sqlite 需要 db_url 或 db_file"
                    )
                if req.db_file:
                    db_file_path = os.path.join(db_dir, f"{uuid.uuid4()}_{req.db_file.filename}")
                    with open(db_file_path, "wb") as f:
                        f.write(await req.db_file.read())
                    sqlite_url = db_file_path
                    if test_db_connection(req.db_type, path=sqlite_url):
                        logger.info(f"Successfully connected to SQLite database at {sqlite_url}")
                    else:
                        return JSONResponse(
                            status_code=400, content="无法连接到 SQLite 数据库，请检查文件是否有效"
                        )

            elif req.db_type == "mysql":
                logger.info("尝试连接到 MySQL 数据库")
                if test_db_connection(
                    req.db_type,
                    host=req.host,
                    port=req.port,
                    user=req.user,
                    password=req.password,
                    database=req.dbname,
                ):
                    logger.info(
                        f"Successfully connected to MySQL database at {req.host}:{req.port}/{req.dbname}"
                    )
                else:
                    return JSONResponse(
                        status_code=400, content="无法连接到 MySQL 数据库，请检查连接信息是否正确"
                    )

            elif req.db_type == "postgres":
                logger.info("尝试连接到 Postgres 数据库")
                if test_db_connection(
                    req.db_type,
                    host=req.host,
                    port=req.port,
                    user=req.user,
                    password=req.password,
                    database=req.dbname,
                ):
                    logger.info(
                        f"Successfully connected to Postgres database at {req.host}:{req.port}/{req.dbname}"
                    )
                else:
                    return JSONResponse(
                        status_code=400,
                        content="无法连接到 Postgres 数据库，请检查连接信息是否正确",
                    )

            elif req.db_type == "oracle":
                logger.info("尝试连接到 Oracle 数据库")
                if test_db_connection(
                    req.db_type, user=req.user, password=req.password, database=req.dsn
                ):
                    logger.info(f"Successfully connected to Oracle database at {req.dsn}")
                else:
                    return JSONResponse(
                        status_code=400, content="无法连接到 Oracle 数据库，请检查连接信息是否正确"
                    )

            elif req.db_type == "duckdb":
                logger.info("尝试连接到 DuckDB")
                if test_db_connection(req.db_type, path=req.db_url):
                    logger.info(f"Successfully connected to DuckDB database at {req.db_url}")
                else:
                    return JSONResponse(
                        status_code=400, content="无法连接到 DuckDB 数据库，请检查连接信息是否正确"
                    )

            elif req.db_type == "excel":
                logger.info("尝试解析 Excel")
                if not req.db_file:
                    return JSONResponse(status_code=400, content="解析 Excel 需要 ecxcel文件")
                temp_file_path = os.path.join(
                    temp_file_dir, f"{uuid.uuid4()}_{req.db_file.filename}"
                )
                db_file_path = os.path.join(db_dir, f"{uuid.uuid4()}.sqlite")
                with open(temp_file_path, "wb") as f:
                    f.write(await req.db_file.read())
                try:
                    await run_in_threadpool(excel_to_sqlite, temp_file_path, db_file_path)
                    try:
                        os.remove(temp_file_path)
                    except Exception as e:
                        logger.error(f"Error deleting temp file: {str(e)}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error parsing Excel: {str(e)}", exc_info=True)
                    return JSONResponse(
                        status_code=400, content="无法解析 Excel 文件，请检查数据是否异常"
                    )

            elif req.db_type == "csv":
                logger.info("尝试解析 CSV")
                if not req.db_file:
                    return JSONResponse(status_code=400, content="解析 CSV 需要 csv文件")

                temp_file_path = os.path.join(
                    temp_file_dir, f"{uuid.uuid4()}_{req.db_file.filename}"
                )
                db_file_path = os.path.join(db_dir, f"{uuid.uuid4()}.sqlite")
                with open(temp_file_path, "wb") as f:
                    f.write(await req.db_file.read())
                try:
                    await run_in_threadpool(csv_to_sqlite, temp_file_path, db_file_path)
                    try:
                        os.remove(temp_file_path)
                    except Exception as e:
                        logger.error(f"Error deleting temp file: {str(e)}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error parsing CSV: {str(e)}", exc_info=True)
                    return JSONResponse(
                        status_code=400, content="无法解析 CSV 文件，请检查数据是否异常"
                    )

            # TODO: 添加更多数据源支持

            else:
                logger.error(f"不支持的数据源类型: {req.db_type}")
                return JSONResponse(status_code=400, content=f"不支持的数据源类型: {req.db_type}")

        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}", exc_info=True)
            return JSONResponse(status_code=400, content=f"无法连接到数据源，错误信息: {str(e)}")
        # 保存到 ORM
        collection_prefix = str(uuid.uuid4())
        conn_info = DBConnection(
            user_id=str(current_user.id),
            name=req.name,
            db_description=req.db_description,
            db_type=req.db_type,
            host=req.host,
            port=req.port,
            username=req.user,
            password=req.password,  # ⚠️ 建议加密存储
            database=req.dbname,
            db_url=req.db_url,
            db_file_path=(
                db_file_path if req.db_type in ["sqlite", "excel", "csv"] and req.db_file else None
            ),
            dsn=req.dsn,
            collection_prefix=collection_prefix,
        )
        db.add(conn_info)
        await db.commit()
        await db.refresh(conn_info)
        try:
            logger.info(f"Initializing db connection, select tables: {req.train_tables}")
            await run_in_threadpool(
                init_db_connection,
                conn_info,
                collection_prefix=str(conn_info.collection_prefix),
                db_type=str(conn_info.db_type),
                train_tables=req.train_tables,
            )
        except Exception as e:
            logger.error(f"Error initializing db connection: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=400, content=f"无法初始化数据库连接，错误信息: {str(e)}"
            )

        return JSONResponse(
            content={"message": "init connection successful", "connection_id": conn_info.id}
        )

    except Exception as e:
        logger.error(f"Error connecting db: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content=f"初始化失败，服务器内部错误: {str(e)}")


@router.get("/list", summary="列出用户所有连接")
async def list_connections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Listing connections for user_id: {current_user.id}")
    try:
        result = await db.execute(
            select(DBConnection)
            .where(DBConnection.user_id == str(current_user.id))
            .order_by(DBConnection.created_at.desc())
        )
        rows = result.scalars().all()
        return [r.get_safe_info() for r in rows]
    except Exception as e:
        logger.error(f"Error listing connections: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content=str(e))


# 列出单个连接信息
@router.get("/info/{connection_id}", summary="获取单个连接信息")
async def get_connection_info(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"Getting connection info for connection_id: {connection_id}, user_id: {current_user.id}"
    )
    try:
        result = await db.execute(select(DBConnection).where(DBConnection.id == connection_id))
        conn = result.scalar_one_or_none()
        if not conn:
            return JSONResponse(status_code=404, content="Not found connection")
        if conn.user_id != str(current_user.id):
            return JSONResponse(status_code=404, content="Not found connection")

        logger.info(f"Retrieved connection info for connection_id: {connection_id}")
        return conn.get_safe_info()
    except Exception as e:
        logger.error(f"Error getting connection info: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content=str(e))


@router.delete("/disconnect/{connection_id}", summary="删除数据源连接及其相关文件")
async def disconnect_db(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(DBConnection)
            .where(DBConnection.id == connection_id)
            .where(DBConnection.user_id == str(current_user.id))
        )
        conn = result.scalar_one_or_none()
        if not conn:
            return JSONResponse(status_code=404, content="连接不存在")
        collection_prefix = conn.collection_prefix
        if collection_prefix:
            try:
                await run_in_threadpool(delete_db_collections, str(collection_prefix))
            except Exception as e:
                logger.warning(
                    f"Error deleting collection {collection_prefix}: {str(e)}", exc_info=True
                )
        try:
            if conn.db_file_path is not None:
                os.remove(conn.db_file_path)
            logger.info(f"删除数据库文件 {conn.db_file_path} 成功")
        except Exception as e:
            logger.warning(f"Error deleting db file {conn.db_file_path}: {str(e)}", exc_info=True)
        await db.delete(conn)
        await db.commit()
        return JSONResponse(content={"message": f"连接 {connection_id} 已断开"})
    except Exception as e:
        logger.error(f"Error disconnecting db: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content=str(e))


# 修改数据源连接的名字和描述
@router.post("/update/{connection_id}", summary="更新数据源连接信息")
async def update_connection_info(
    connection_id: int,
    req: UpdateDBConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(DBConnection)
            .where(DBConnection.id == connection_id)
            .where(DBConnection.user_id == str(current_user.id))
        )
        conn = result.scalar_one_or_none()
        if not conn:
            return JSONResponse(status_code=404, content="连接不存在")
        if req.new_name:
            conn.name = req.new_name
        if req.new_description:
            conn.db_description = req.new_description
        db.add(conn)
        await db.commit()
        await db.flush()
        await db.refresh(conn)
        return JSONResponse(content={"message": f"连接 {conn.id} 已更新"})
    except Exception as e:
        logger.error(f"Error updating connection info: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content=str(e))
