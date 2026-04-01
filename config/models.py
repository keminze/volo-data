from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def get_info(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at,
        }


class DBConnection(Base):
    __tablename__ = "db_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    db_type: Mapped[str] = mapped_column(String(50), nullable=False)

    db_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="数据源描述")

    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    database: Mapped[str | None] = mapped_column(String(255), nullable=True)

    db_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # sqlite / duckdb

    db_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # sqlite

    dsn: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Oracle

    collection_prefix: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="向量数据库集合的前缀",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="db_connection",
        passive_deletes=True,
    )

    def get_db_info(self) -> dict[str, Any]:
        return {
            "db_type": self.db_type,
            "db_description": self.db_description,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "database": self.database,
            "db_url": self.db_url,
            "db_file_path": self.db_file_path,
            "dsn": self.dsn,
        }

    def get_safe_info(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "db_type": self.db_type,
            "db_description": self.db_description,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "db_url": self.db_url,
            "created_at": self.created_at,
        }


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)

    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="对话名称",
    )

    connection_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("db_connections.id", ondelete="SET NULL"),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="对话描述",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    db_connection: Mapped["DBConnection"] = relationship(
        "DBConnection",
        back_populates="conversations",
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    generate_history: Mapped[list["GenerateHistory"]] = relationship(
        "GenerateHistory",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def get_info(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "connection_id": self.connection_id,
            "description": self.description,
            "created_at": self.created_at,
        }


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="消息类型",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容",
    )

    sql: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="生成的 SQL",
    )

    sample_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="样例数据",
    )

    charts: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="ECharts 图表数据",
    )

    compute_code: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="计算代码",
    )

    code_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="代码执行结果",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def get_info(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "sql": self.sql,
            "sample_data": self.sample_data,
            "charts": self.charts,
            "compute_code": self.compute_code,
            "code_result": self.code_result,
            "created_at": self.created_at,
        }


class GenerateHistory(Base):
    __tablename__ = "generate_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    run_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="langgraph 运行 ID",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="generate_history",
    )
