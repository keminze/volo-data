# experimental_agent

基于 [deepagents](https://pypi.org/project/deepagents/) 框架构建的对话式数据分析 Agent 应用。

## 架构

```
experimental_agent/
├── __init__.py       # 包入口，导出 create_analyst_agent
├── agent.py          # Agent 构建（deepagents create_deep_agent）
├── tools.py          # 数据分析工具集（5 个 @tool 函数）
├── server.py         # FastAPI 服务（普通 + SSE 流式接口）
├── example.py        # 直接调用示例
└── README.md
```

## 与原有工作流的关系

| 对比项 | 原有工作流（LangGraph） | deepagents Agent |
|--------|------------------------|-----------------|
| 驱动方式 | 固定节点 DAG，按序执行 | ReAct 循环，LLM 自主决策调用工具 |
| 灵活性 | 低（节点顺序固定） | 高（LLM 按需选择工具） |
| 可扩展性 | 需修改图结构 | 直接添加 `@tool` 函数 |
| 复用代码 | — | 复用 `services/tools.py` 中的核心逻辑 |

## 工具列表

| 工具 | 功能 |
|------|------|
| `list_available_datasources` | 列出可用数据源 |
| `execute_sql_query` | 自然语言 → SQL → 执行查询 |
| `decide_and_run_compute` | 判断并执行 Python 二次计算 |
| `generate_charts` | 生成 ECharts 图表配置 |
| `generate_analysis_report` | 生成商业洞察报告 |

## 快速开始

### 1. 环境配置

在安装好主项目依赖的同时，你还需安装 deepagents：
```bash
pip intsall deepagents
```

在项目根目录 `.env` 中确保配置了以下变量（与主项目共用）：

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=your_database

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Agent 默认数据源（collection_prefix 对应 ChromaDB 集合）
DEFAULT_COLLECTION_PREFIX=your_prefix
DEFAULT_DB_TYPE=mysql
```

### 2. 启动 API 服务

```bash
cd e:/github-project/volo-data
uvicorn experimental_agent.server:app --reload --port 8001
```

### 3. 调用接口

**普通对话：**
```bash
curl -X POST http://localhost:8001/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "查询最近30天的总销售额"}],
    "datasource": {
      "collection_prefix": "your_prefix",
      "db_params": {
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "username": "root",
        "password": "xxx",
        "database": "your_db"
      }
    }
  }'
```

**SSE 流式对话：**
```bash
curl -N -X POST http://localhost:8001/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "分析销售趋势"}]}'
```

SSE 事件格式：
```
event: token
data: {"text": "根据"}

event: tool_start
data: {"tool": "execute_sql_query", "args": {...}}

event: tool_result
data: {"tool": "execute_sql_query", "result": "..."}

event: done
data: {"session_id": "xxx"}
```

### 4. 直接在 Python 中使用

```python
import asyncio
from experimental_agent.agent import create_analyst_agent

async def main():
    agent = create_analyst_agent()
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": "你好"}]
    })
    print(result["messages"][-1].content)

asyncio.run(main())
```

或运行内置示例：
```bash
python experimental_agent/example.py
```
