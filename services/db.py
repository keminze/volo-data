import os
import re
import sqlite3
from enum import Enum
from pathlib import Path

import chardet
import chromadb
import pandas as pd
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from config.logging_config import logger
from config.models import DBConnection
from services.prompt import Generate_DDL_Summary_Prompt
from services.vanna_service import Vanna

load_dotenv()

CollectionSuffix = Enum(
    "CollectionSuffix", {"DOCUMENTATION": "documentation", "DDL": "ddl", "SQL": "sql"}
)

llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_BASE_URL"),
)

chromadb_client = chromadb.HttpClient(host=os.getenv("CHROMA_HOST"), port=os.getenv("CHROMA_PORT"))


def generate_ddl_summary_tool(ddl: str):
    """根据数据生成 SQL"""
    try:
        # print("generate_sql_tool start",datetime.datetime.now())
        prompt = ChatPromptTemplate.from_template(Generate_DDL_Summary_Prompt)
        chain = prompt | llm  # LCEL 风格
        resp = chain.invoke({"ddl": ddl})
        logger.info(f"generate_sql_tool result: {resp.content.strip()}")
        return resp.content.strip()
    except Exception as e:
        logger.error(f"Error in generate_sql_tool:{str(e)}", exc_info=True)
        return ""


def delete_db_collections(collection_prefix: str):
    """删除DQrant中的对话相关集合"""
    try:

        for suffix in CollectionSuffix:
            collection_name = f"{collection_prefix}_{suffix.value}"
            try:
                # qd_client.delete_collection(collection_name=collection_name)
                chromadb_client.delete_collection(name=collection_name)
                logger.info(f"Deleted collection: {collection_name}")
            except Exception as e:
                logger.warning(
                    f"Collection not found, cannot delete: {collection_name}, error: {str(e)}",
                    exc_info=True,
                )
                raise e

    except Exception as e:
        logger.error(f"Error deleting collections or directory: {str(e)}", exc_info=True)
        raise e


def connect_to_database(vn: Vanna, db_params):
    logger.info(f"Connecting to database with params: {db_params}")
    db_type = db_params.get("db_type")
    # logger.info
    vn.config["additional_prompt"] = db_params.get("db_description", None)
    try:
        if db_type == "sqlite":
            logger.info("Connecting to SQLite database")
            sqlite_url = db_params.get("db_url")
            if db_params.get("db_file_path"):
                sqlite_url = db_params.get("db_file_path")
            vn.connect_to_sqlite(sqlite_url)

        elif db_type == "csv" or db_type == "excel":
            vn.connect_to_sqlite(db_params.get("db_file_path"))

        elif db_type == "mysql":
            logger.info("Connecting to MySQL database")
            vn.connect_to_mysql(
                host=db_params.get("host"),
                port=db_params.get("port") or 3306,
                user=db_params.get("username"),
                password=db_params.get("password"),
                dbname=db_params.get("database"),
            )

        elif db_type == "postgres":
            logger.info("Connecting to Postgres database")
            vn.connect_to_postgres(
                host=db_params.get("host"),
                port=db_params.get("port") or 5432,
                user=db_params.get("username"),
                password=db_params.get("password"),
                dbname=db_params.get("database"),
            )

        elif db_type == "oracle":
            logger.info("Connecting to Oracle database")
            vn.connect_to_oracle(
                user=db_params.get("username"),
                password=db_params.get("password"),
                dsn=db_params.get("dsn"),
            )

        elif db_type == "duckdb":
            logger.info("Connecting to DuckDB")
            vn.connect_to_duckdb(url=db_params.get("db_url"))
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}", exc_info=True)
        raise ValueError(f"Unable to connect to database, error: {str(e)}") from e


def init_db_connection(
    req: DBConnection, collection_prefix: str, db_type: str, train_tables: list | None
):

    vn = Vanna(
        {
            "client": chromadb_client,
            # "client": qd_client,
            "documentation_collection_name": f"{collection_prefix}_{CollectionSuffix.DOCUMENTATION.value}",
            "ddl_collection_name": f"{collection_prefix}_{CollectionSuffix.DDL.value}",
            "sql_collection_name": f"{collection_prefix}_{CollectionSuffix.SQL.value}",
        }
    )

    try:
        if db_type == "sqlite":
            logger.info("连接到 SQLite 数据库")
            if not req.db_url and not req.db_file_path:
                raise ValueError("初始化 sqlite 文件未找到")
            sqlite_url = req.db_url
            if req.db_file_path:
                sqlite_url = req.db_file_path
            vn.connect_to_sqlite(sqlite_url)
            df_ddl = vn.run_sql("SELECT type, sql FROM sqlite_master WHERE sql is not null")
            for ddl in df_ddl["sql"].to_list():
                ddl_summary = generate_ddl_summary_tool(ddl)
                ddl_information = f"Summary:{ddl_summary} DDL:{ddl}"
                vn.train(ddl=ddl_information)

        elif db_type == "csv" or db_type == "excel":
            logger.info("连接到表格文件")
            vn.connect_to_sqlite(req.db_file_path)
            df_ddl = vn.run_sql("SELECT type, sql FROM sqlite_master WHERE sql is not null")
            for ddl in df_ddl["sql"].to_list():
                ddl_summary = generate_ddl_summary_tool(ddl)
                ddl_information = f"Summary:{ddl_summary} DDL:{ddl}"
                vn.train(ddl=ddl_information)

        elif db_type == "mysql":
            logger.info("连接到 MySQL 数据库")
            vn.connect_to_mysql(
                host=req.host,
                port=req.port or 3306,
                user=req.username,
                password=req.password,
                dbname=req.database,
            )
            base_sql = f"""
                SELECT CONCAT('SHOW CREATE TABLE `', TABLE_NAME, '`;') AS ddl_query
                FROM information_schema.tables
                WHERE table_schema = '{req.database}'
            """

            if train_tables:  # 非空时筛选指定表
                placeholders = ", ".join([f"'{t}'" for t in train_tables])
                base_sql += f" AND TABLE_NAME IN ({placeholders})"

            base_sql += ";"  # 结尾加分号
            df_ddl_query = vn.run_sql(base_sql)

            logger.info(f"MySQL DDL queries: {df_ddl_query['ddl_query'].to_list()}")
            for ddl_query in df_ddl_query["ddl_query"].to_list():
                df_ddl = vn.run_sql(ddl_query)
                # logger.info(f"MySQL DDL: {df_ddl.iloc[0,1]}")
                ddl = df_ddl.iloc[0, 1]
                ddl_summary = generate_ddl_summary_tool(ddl)
                ddl_information = f"Summary:{ddl_summary} DDL:{ddl}"
                vn.train(ddl=ddl_information)

        elif db_type == "postgres":
            logger.info("连接到 Postgres 数据库")
            vn.connect_to_postgres(
                host=req.host,
                port=req.port or 5432,
                user=req.username,
                password=req.password,
                dbname=req.database,
            )
            base_sql = f"""
                SELECT CONCAT('SHOW CREATE TABLE `', TABLE_NAME, '`;') AS ddl_query
                FROM information_schema.tables
                WHERE table_schema = '{req.database}'
            """

            if train_tables:  # 非空时筛选指定表
                placeholders = ", ".join([f"'{t}'" for t in train_tables])
                base_sql += f" AND TABLE_NAME IN ({placeholders})"

            base_sql += ";"  # 结尾加分号
            df_ddl_query = vn.run_sql(base_sql)

            logger.info(f"Postgres DDL queries: {df_ddl_query['ddl_query'].to_list()}")
            for ddl_query in df_ddl_query["ddl_query"].to_list():
                df_ddl = vn.run_sql(ddl_query)
                # logger.info(f"MySQL DDL: {df_ddl.iloc[0,1]}")
                ddl = df_ddl.iloc[0, 1]
                ddl_summary = generate_ddl_summary_tool(ddl)
                ddl_information = f"Summary:{ddl_summary} DDL:{ddl}"
                vn.train(ddl=ddl_information)

        elif db_type == "oracle":
            logger.info("连接到 Oracle 数据库")
            vn.connect_to_oracle(
                user=req.username,
                password=req.password,
                dsn=req.dsn,
            )
            df_information_schema = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS")
            plan = vn.get_training_plan_generic(df_information_schema)
            logger.info(f"Oracle training plan: {plan.get_summary()}")
            vn.train(plan=plan)

        elif db_type == "duckdb":
            logger.info("连接到 DuckDB")
            vn.connect_to_duckdb(url=req.db_url)
            df_information_schema = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS")
            plan = vn.get_training_plan_generic(df_information_schema)
            logger.info(f"DuckDB training plan: {plan.get_summary()}")
            vn.train(plan=plan)

        # TODO: 添加更多数据库支持

        else:
            logger.error(f"不支持的数据库类型: {db_type}")
            raise ValueError(f"无法初始化数据库，错误信息: 不支持{db_type}")
        # vn._client.delete_collection()
        return
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}", exc_info=True)
        raise ValueError(f"无法初始化数据库，错误信息: {str(e)}") from e


def test_db_connection(db_type: str, **kwargs) -> bool:
    """
    验证数据库是否可以连接
    支持 SQLite、MySQL、PostgreSQL、Oracle、DuckDB

    参数:
        db_type: str - 'sqlite' | 'mysql' | 'postgresql' | 'oracle' | 'duckdb'
        其他参数:
            - 对于 sqlite/duckdb: path (数据库文件路径)
            - 对于 mysql/postgresql/oracle: host, port, user, password, database
    返回:
        True 表示可以连接，False 表示连接失败
    """
    try:
        if db_type == "sqlite":
            db_url = f"sqlite:///{kwargs['path']}"
        elif db_type == "duckdb":
            db_url = f"duckdb:///{kwargs['path']}"
        elif db_type == "mysql":
            # 需要安装 mysqlclient 或 pymysql
            user = kwargs["user"]
            password = kwargs["password"]
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 3306)
            db = kwargs["database"]
            db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
        elif db_type == "postgresql":
            user = kwargs["user"]
            password = kwargs["password"]
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 5432)
            db = kwargs["database"]
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        elif db_type == "oracle":
            user = kwargs["user"]
            password = kwargs["password"]
            dsn = kwargs["dsn"]
            db_url = f"oracle+cx_oracle://{user}:{password}@{dsn}"
        else:
            raise ValueError(f"Unsupported Data Source: {db_type}")

        # 尝试连接
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Database connection successful: {db_type}")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {str(e)}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return False


def get_db_tables(db_type: str, **kwargs):
    """
    验证数据库是否可以连接，并返回数据库中所有表名与注释

    支持 SQLite、MySQL、PostgreSQL、Oracle、DuckDB

    参数:
        db_type: str - 'sqlite' | 'mysql' | 'postgresql' | 'oracle' | 'duckdb'
        其他参数:
            - 对于 sqlite/duckdb: path (数据库文件路径)
            - 对于 mysql/postgresql/oracle: host, port, user, password, database

    返回:
        (success: bool, tables: list[dict] | None)
        - 成功时返回 (True, [{"table_name": str, "comment": str}, ...])
        - 失败时返回 (False, None)
    """
    try:
        if db_type == "sqlite":
            db_url = f"sqlite:///{kwargs['path']}"
        elif db_type == "duckdb":
            db_url = f"duckdb:///{kwargs['path']}"
        elif db_type == "mysql":
            user = kwargs["user"]
            password = kwargs["password"]
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 3306)
            db = kwargs["database"]
            db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
        elif db_type == "postgresql":
            user = kwargs["user"]
            password = kwargs["password"]
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 5432)
            db = kwargs["database"]
            db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        elif db_type == "oracle":
            user = kwargs["user"]
            password = kwargs["password"]
            dsn = kwargs["dsn"]
            db_url = f"oracle+cx_oracle://{user}:{password}@{dsn}"
        else:
            raise ValueError(f"Unsupported Data Source: {db_type}")

        # 创建连接
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))  # 测试连接

            inspector = inspect(engine)
            tables = inspector.get_table_names()

            result = []

            if db_type == "mysql":
                # 查询表注释
                schema = kwargs["database"]
                rows = conn.execute(
                    text("""
                        SELECT TABLE_NAME, TABLE_COMMENT
                        FROM information_schema.tables
                        WHERE table_schema = :schema
                    """),
                    {"schema": schema},
                ).fetchall()
                comment_map = {r[0]: r[1] or "" for r in rows}
                result = [{"table_name": t, "comment": comment_map.get(t, "")} for t in tables]

            elif db_type == "postgresql":
                rows = conn.execute(text("""
                        SELECT c.relname AS table_name, obj_description(c.oid) AS comment
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                    """)).fetchall()
                comment_map = {r[0]: r[1] or "" for r in rows}
                result = [{"table_name": t, "comment": comment_map.get(t, "")} for t in tables]

            elif db_type == "oracle":
                rows = conn.execute(text("""
                        SELECT table_name, comments
                        FROM user_tab_comments
                    """)).fetchall()
                comment_map = {r[0]: r[1] or "" for r in rows}
                result = [{"table_name": t, "comment": comment_map.get(t, "")} for t in tables]

            else:
                # SQLite / DuckDB 不支持注释
                result = [{"table_name": t, "comment": ""} for t in tables]

        engine.dispose()
        logger.info(f"Database connection successful: {db_type}, tables: {len(tables)} found")
        return True, result

    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {str(e)}", exc_info=True)
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return False, None


def clean_and_validate_df(
    df: pd.DataFrame,
    *,
    date_detection: bool = True,
    date_sample_size: int = 200,
    date_threshold: float = 0.8,
) -> pd.DataFrame:
    """
    对 DataFrame 做质量检查 + 格式标准化：
      - 检查空表头、严重缺失值
      - 统一识别 & 格式化日期字段为 yyyy-mm-dd（只有当识别率高时）
      - 百分比转为小数
    参数:
      - date_detection: 是否启用自动日期检测
      - date_sample_size: 每列检测时抽样大小
      - date_threshold: 识别率阈值（>=认为是日期列）
    """
    # 1️⃣ 表头检查
    if df.columns.isnull().any():
        raise ValueError("表头中存在空列名，请先处理再导入")

    # 2️⃣ 清理列名：去掉特殊字符，替换空格
    df = df.copy()
    df.columns = [re.sub(r"\W+", "_", str(col)).strip("_") for col in df.columns]

    # 3️⃣ 严重缺失值（如果全为空）
    if len(df.dropna(how="all")) == 0:
        raise ValueError("整个表都是缺失值，请检查文件")

    # 4️⃣ 统一日期字段格式
    if date_detection:
        for col in df.columns:
            # 如果已经是 datetime dtype，直接格式化
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
                    continue
            except Exception:
                # 如果类型检查出错，跳过自动处理
                pass

            # 只检测非数值、非空的样本
            sample = df[col].dropna().astype(str).head(date_sample_size)
            if sample.empty:
                continue

            # 尝试把 sample 转为 datetime
            parsed = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
            nonnull_ratio = parsed.notna().sum() / len(sample)

            # 识别率高于阈值，才把整列转成日期格式
            if nonnull_ratio >= date_threshold:
                converted_full = pd.to_datetime(
                    df[col], errors="coerce", infer_datetime_format=True
                )
                df[col] = converted_full.dt.strftime("%Y-%m-%d")
                logger.debug(f"列 {col} 被识别为日期列并格式化 (识别率={nonnull_ratio:.2f})")

    # 5️⃣ 百分比转为小数（仅对字符串形式的百分号做转换）
    for col in df.columns:
        if df[col].dtype == object:

            def _pct_to_float(x):
                try:
                    if isinstance(x, str) and x.strip().endswith("%"):
                        s = x.strip().replace("%", "")
                        # 处理千位分隔符
                        s = s.replace(",", "")
                        return float(s) / 100.0
                    return x
                except Exception:
                    return x

            df[col] = df[col].apply(_pct_to_float)

    return df


def read_csv_auto(csv_file, **kwargs):
    # 先检测编码
    with open(csv_file, "rb") as f:
        raw = f.read(4096)  # 取前4KB
    result = chardet.detect(raw)
    encoding = result["encoding"] or "utf-8"
    print(f"检测到编码: {encoding}")

    # 遇到gb2312/GBK优先用gb18030
    if encoding and encoding.lower() in ("gb2312", "gbk"):
        encoding = "gb18030"

    # 保底 utf-8-sig
    if not encoding:
        encoding = "utf-8-sig"

    return pd.read_csv(csv_file, encoding=encoding, **kwargs)


def csv_to_sqlite(csv_path: str, sqlite_path: str, *, enforce_str: bool = True):
    """
    将 CSV 文件保存为 SQLite 表（含数据质量检查+格式标准化）
    - enforce_str=True: 读取 CSV 时用 dtype=str，避免 pandas 自动把列解析为数值/日期
    """
    csv_file = Path(csv_path)

    if not csv_file.exists():
        raise FileNotFoundError(f"未找到 CSV 文件: {csv_file}")

    # 读取 CSV（强制为字符串以避免自动解析）
    if enforce_str:
        df = read_csv_auto(csv_file, dtype=str, keep_default_na=True, na_values=["", "NA", "N/A"])
    else:
        df = read_csv_auto(csv_file)

    logger.info(f"读取 CSV: {csv_file.name}, 行数: {len(df)}")

    if df.empty:
        logger.error(f"CSV '{csv_file.name}' 为空")
        raise ValueError("CSV 为空")

    # 清洗+标准化（默认启用日期检测）
    df = clean_and_validate_df(df)

    table_name = re.sub(r"\W+", "_", csv_file.stem)

    conn = sqlite3.connect(sqlite_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

    logger.info(f"CSV '{csv_file.name}' 已写入表 '{table_name}' 到 {sqlite_path}")


def excel_to_sqlite(excel_path: str, sqlite_path: str, *, enforce_str: bool = True):
    """
    将 Excel 每个 sheet 转为 SQLite 中的表
    - enforce_str=True: 读取 Excel 时尝试把所有列读为字符串，避免 Excel 的日期单元格变成 datetime dtype
    注意：pandas.read_excel 的 dtype 参数在某些 pandas 版本下对所有引擎可能有限制，
    如果 dtype=str 无效，可以使用 converters 来逐列强制 str。
    """
    excel_file = Path(excel_path)
    if not excel_file.exists():
        raise FileNotFoundError(f"未找到 Excel 文件: {excel_file}")

    conn = sqlite3.connect(sqlite_path)

    with pd.ExcelFile(excel_file) as xls:
        for sheet_name in xls.sheet_names:
            if enforce_str:
                # 读取时尽量把值当字符串读入，避免 Excel 的日期/数值自动解析
                try:
                    df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str)
                except TypeError:
                    # 某些 pandas 版本/engine 不支持 dtype 参数，退回到 converters
                    df = pd.read_excel(
                        xls,
                        sheet_name=sheet_name,
                        converters=lambda v: str(v) if v is not None else v,
                    )
            else:
                df = pd.read_excel(xls, sheet_name=sheet_name)

            if df.empty:
                logger.warning(f"Sheet '{sheet_name}' 为空，跳过")
                continue

            try:
                df = clean_and_validate_df(df)
            except Exception as e:
                logger.error(f"Sheet '{sheet_name}' 数据异常: {e}", exc_info=True)
                raise ValueError(f"Sheet '{sheet_name}' 数据异常: {e}") from e

            table_name = re.sub(r"\W+", "_", sheet_name)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            logger.info(f"Sheet '{sheet_name}' 已写入表 '{table_name}'")

    conn.commit()
    conn.close()
    logger.info(f"所有有效 sheet 已写入 {sqlite_path}")
