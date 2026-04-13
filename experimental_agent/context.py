"""
AgentContext — 每次请求的运行时上下文定义。

通过 deepagents 的 context_schema + ToolRuntime 机制，将用户身份、
数据源配置等信息安全地传递给所有工具，无需在消息体中明文传递。
"""

from dataclasses import dataclass, field


@dataclass
class DatasourceConfig:
    """单个数据源的连接配置。"""
    collection_prefix: str = ""
    db_params: dict = field(default_factory=dict)


@dataclass
class AgentContext:
    """
    每次 Agent 调用的运行时上下文。

    通过 agent.invoke(..., context=AgentContext(...)) 传入，
    工具函数通过 runtime: ToolRuntime[AgentContext] 参数读取。

    Fields:
        user_id:        用户唯一标识，用于隔离每用户记忆
        datasource:     当前请求使用的数据源配置
        allow_hitl:     是否允许人机交互（需要用户确认的操作）
        language:       用户偏好语言（zh / en）
    """
    user_id: str = "anonymous"
    datasource: DatasourceConfig = field(default_factory=DatasourceConfig)
    allow_hitl: bool = True
    language: str = "zh"
