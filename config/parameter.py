from typing import Optional

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, Field


class DBConnectRequest(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    db_type: Optional[str] = None
    db_description: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    dbname: Optional[str] = None
    db_url: Optional[str] = None
    dsn: Optional[str] = None
    db_file: Optional[UploadFile] = None  # 文件上传
    train_tables: Optional[list] = None

    @classmethod
    def as_form(
        cls,
        user_id: str = Form(..., description="用户 ID"),
        name: str = Form(..., description="数据源名称"),
        db_type: str = Form(
            ..., description="数据源类型，支持 sqlite/mysql/postgres/oracle/duckdb/excel/csv"
        ),
        db_description: Optional[str] = Form(None, description="数据源描述(对LLM理解数据有帮助)"),
        host: Optional[str] = Form(None, description="数据库主机"),
        port: Optional[int] = Form(None, description="数据库端口"),
        user: Optional[str] = Form(None, description="数据库用户"),
        password: Optional[str] = Form(None, description="数据库密码"),
        dbname: Optional[str] = Form(None, description="数据库名称"),
        db_url: Optional[str] = Form(
            None, description="数据库 URL ，仅 sqlite 和 duckdb 使用。 sqlite 推荐文件安全上传。"
        ),
        dsn: Optional[str] = Form(None, description="数据源名称，仅 Oracle 使用"),
        db_file: Optional[UploadFile] = File(
            None, description="上传的数据库文件，仅 sqlite、excel、csv 使用"
        ),
        train_tables: Optional[list] = Form(
            None, description="指定训练的表，仅数据库类型的数据源使用"
        ),
    ):
        return cls(
            user_id=user_id,
            name=name,
            db_type=db_type,
            db_description=db_description,
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            db_url=db_url,
            dsn=dsn,
            db_file=db_file,
            train_tables=train_tables,
        )

    @classmethod
    def as_connect_request(
        cls,
        db_type: str = Form(
            ..., description="数据源类型，支持 sqlite/mysql/postgres/oracle/duckdb/excel/csv"
        ),
        host: Optional[str] = Form(None, description="数据库主机"),
        port: Optional[int] = Form(None, description="数据库端口"),
        user: Optional[str] = Form(None, description="数据库用户"),
        password: Optional[str] = Form(None, description="数据库密码"),
        dbname: Optional[str] = Form(None, description="数据库名称"),
        db_url: Optional[str] = Form(
            None, description="数据库 URL ，仅 sqlite 和 duckdb 使用。 sqlite 推荐文件安全上传。"
        ),
        dsn: Optional[str] = Form(None, description="数据源名称，仅 Oracle 使用"),
        db_file: Optional[UploadFile] = File(
            None, description="上传的数据库文件，仅 sqlite、excel、csv 使用"
        ),
    ):
        return cls(
            db_type=db_type,
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            db_url=db_url,
            dsn=dsn,
            db_file=db_file,
        )


class UpdateDBConnectRequest(BaseModel):
    user_id: str = Field(..., description="用户 ID")

    new_name: str | None = Field(default=None, description="新的数据源名称")

    new_description: str | None = Field(
        default=None, description="新的数据源描述(对LLM理解数据有帮助)"
    )


class ConversationCreate(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    name: str | None = Field(None, description="对话名称")
    connection_id: Optional[int] = Field(None, description="关联的数据源连接 ID")
    description: Optional[str] = Field(None, description="任务背景")


class GenerateRequest(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    conversation_id: int = Field(..., description="对话 ID")
    input: str = Field(..., description="用户查询输入")
    allow_llm_to_see_data: bool = Field(False, description="是否允许大语言模型访问数据")
    skip_charts: bool = Field(True, description="True:跳过生成图表的节点;False:经过生成图表的节点")
    skip_report: bool = Field(True, description="True:跳过生成报告的节点;False:经过生成报告的节点")
