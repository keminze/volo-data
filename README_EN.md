# 🚀 VoloData

[English](./README_EN.md) | [中文](./README.md)

<p align="center">
  <img src="./frontend/src/app/favicon.ico" width="40">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache2.0-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.110%2B-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/langgraph-1.0%2B-green" alt="LangGraph">
  <img alt="CircleCI" src="https://img.shields.io/circleci/build/github/keminze/volo-data">
  <img src="https://img.shields.io/badge/docker-ready-blue" alt="Docker">
  <img src="https://img.shields.io/github/stars/keminze/volo-data?style=social" alt="Stars">
  <img src="https://img.shields.io/github/forks/keminze/volo-data?style=social" alt="Forks">
</p>

> 🤖 This is an AI-based database interaction platform that supports multi-data source connections, natural language queries, and intelligent dialogue. My purpose in open-sourcing this project is to encourage developers worldwide to make it more secure, professional, and intelligent.

## ❓ Why Use VoloData

### Existing NL2SQL tools usually have the following issues:

* Difficult to connect to multiple data sources
* Lack of extensible AI workflows
* No support for real-time streaming responses

### VoloData provides:

* Deep optimization of LLM prompts in the SQL generation stage of the open-source project [Vanna](https://github.com/vanna-ai/vanna)
* LangGraph AI workflow
* Unified interface for multiple databases
* SSE real-time responses
* Secure code sandbox

## ✨ Key Features

|                 Feature                | Description                                       |
| :------------------------------------: | :------------------------------------------------ |
|    🔗 **Multi-Data Source Support**    | MySQL, PostgreSQL, SQLite, Excel, CSV             |
|      💬 **Natural Language Query**     | AI models convert natural language into SQL       |
| 🧠 **Intelligent Conversation System** | Vector database + conversation history management |
|   ⚡ **Real-time Streaming Response**   | Server-Sent Events (SSE) for instant push         |
|      🔒 **API Key Authentication**     | Built-in security authentication mechanism        |
|     📦 **Docker Containerization**     | Ready-to-use Docker Compose deployment            |
|          🛡️ **Code Sandbox**          | Safely run LLM-generated metric calculation code  |

## 🖼️ Project Preview

### Home

<p align="center">
  <img src="./demo/home.png" width="900">
</p>

### Data Sources

<p align="center">
  <img src="./demo/data.png" width="900">
</p>

### Chat Interface

<p align="center">
  <img src="./demo/chat.png" width="900">
</p>

For more project preview information, please refer to the product user manual (currently under improvement).

## 🏗️ Core Workflow

<p align="center">
  <img src="./demo/workflow.png" width="900">
</p>

## 🛠️ Tech Stack

### Backend

| Framework      | Purpose              |
| :------------- | :------------------- |
| **FastAPI**    | Modern web framework |
| **SQLAlchemy** | ORM framework        |
| **Alembic**    | Database migration   |
| **ChromaDB**   | Vector database      |
| **Redis**      | Cache & queue        |
| **Pydantic**   | Data validation      |
| **LangGraph**  | AI workflow          |

### Frontend

| Framework       | Purpose           |
| :-------------- | :---------------- |
| **Next.js**     | React framework   |
| **TypeScript**  | Type safety       |
| **TailwindCSS** | Styling framework |

### DevOps

| Tool               | Purpose                       |
| :----------------- | :---------------------------- |
| **Docker**         | Containerized deployment      |
| **Docker Compose** | Multi-container orchestration |
| **GitHub Actions** | CI/CD                         |

## 🚀 Quick Deployment

### One-click deployment with Docker

```bash
# Clone the project
git clone https://github.com/keminze/volo-data.git
cd volo-data

# Start all services
docker-compose up -d
```

### One-Click Docker Deployment for Development

Before running the following command, you may modify the `.env.langsmith` file (optional). This allows you to view workflow execution logs in LangSmith. For specific configuration details, please refer to the [LangSmith Docs](https://docs.langchain.com/langsmith/home).

```bash
docker-compose -f docker-compose.dev.yml up -d

```

> ✅ After startup, visit: [http://localhost:3000](http://localhost:3000)

## 📁 Project Structure

```
volo-data/
├── main.py                    # 🏁 Application entry
├── requirements.txt           # 📦 Python dependencies
├── Dockerfile                 # 🐳 Docker configuration
├── docker-compose.yml         # 🧩 Full environment configuration
├── docker-compose.dev.yml     # 💻 Development environment configuration
├── alembic.ini               # 🔄 Database migration configuration
├── redis_client.py           # 📡 Redis client
│
├── config/                   # ⚙️ Configuration module
│   ├── database.py          # Database configuration
│   ├── logging_config.py    # Logging configuration
│   ├── models.py            # SQLAlchemy models
│   └── parameter.py         # Parameter configuration
│
├── routers/                 # 🛤️ API routes
│   ├── connection.py        # Data source connection
│   ├── conversation.py      # Conversation management
│   ├── database.py          # Database operations
│   ├── generate.py          # Task generation
│   └── log.py               # Log query
│
├── services/                # 🧩 Business logic
│   ├── db.py                # Database services
│   ├── graph.py             # Graph related operations
│   ├── graph_sse.py         # SSE streaming responses
│   ├── tools.py             # Utility functions
│   ├── prompt.py            # Prompt management
│   ├── vanna.py             # SQL generation
│   └── log.py               # Log services
│
├── middlewares/             # 🔧 Middleware
│   ├── api_key_middleware.py # API Key authentication
│   └── logging.py            # Logging middleware
│
├── vanna/                   # 🤖 Vanna SQL generation
├── frontend/                # 🎨 Next.js frontend
└── alembic/                 # 🔁 Database migration
```

## Local Development

### Prerequisites

* Python 3.12+
* Node.js 20+

### Steps

```bash
# 1. Clone the project
git clone https://github.com/keminze/volo-data.git
cd volo-data

# 2. Create virtual environment
python -m venv env

# Windows
env\Scripts\activate

# Linux/macOS
source env/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Environment configuration
# Copy .env.example to .env and modify configuration

# 5. Initialize database
alembic upgrade head

# 6. Start backend (port 9000)
python main.py --port 9000

# 7. Start frontend (new terminal)
cd frontend
npm install
npm run dev
```

## 📚 API Documentation

After starting the service, visit:

| Document       | URL                                                        |
| :------------- | :--------------------------------------------------------- |
| **Swagger UI** | [http://localhost:9000/docs](http://localhost:9000/docs)   |
| **ReDoc**      | [http://localhost:9000/redoc](http://localhost:9000/redoc) |

## 🔐 Security Configuration

### API Authentication

All requests must include an API Key:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:9000/connections
```

### Environment Variables

> ⚠️ Sensitive information should be configured via environment variables and **must not** be committed to the repository.

```bash
# Add to .gitignore
echo ".env" >> .gitignore
```

## 🗃️ Database Migration

```bash
# Create new migration
alembic revision --autogenerate -m "describe migration"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

```bash
1. Fork the project
2. Create a feature branch: git checkout -b feature/AmazingFeature
3. Commit your changes: git commit -m 'Add AmazingFeature'
4. Push to the branch: git push origin feature/AmazingFeature
5. Open a Pull Request
```

## ✍️ Future Plans

### Upcoming Features

- Support for more data sources
- SQL security auditing (self-healing / error correction)
- Improved Agent memory management

### Features Under Planning

- Visual dashboards
- Data permissions and row-level filtering
- Enterprise-level document RAG to enhance data analysis accuracy

## 📄 License

This project is licensed under the [Apache 2.0 License](./LICENSE).

## 📬 Contact

| Channel           | Link                                                            |
| :---------------- | :-------------------------------------------------------------- |
| 🐛 Issue Tracking | [Issues](https://github.com/keminze/volo-data/issues)           |
| 💬 Discussion     | [Discussions](https://github.com/keminze/volo-data/discussions) |
| 📧 Email          | [kmz3225147671@gmail.com](mailto:kmz3225147671@gmail.com)       |

## 💖 Acknowledgements

Thanks to the following open-source projects:

| Project                                                                    | Purpose         |
| :------------------------------------------------------------------------- | :-------------- |
| [Vanna](https://github.com/vanna-ai/vanna)                                 | SQL generation  |
| [ChromaDB](https://github.com/chroma-core/chroma)                          | Vector database |
| [FastAPI](https://github.com/tiangolo/fastapi)                             | Web framework   |
| [langchain-sandbox](https://github.com/langchain-ai/langchain-sandbox.git) | Code sandbox    |
| [LangGraph](https://github.com/langchain-ai/langgraph.git)                 | AI workflow     |

## 📊 Project Statistics

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/keminze/volo-data)
![GitHub forks](https://img.shields.io/github/forks/keminze/volo-data)
![GitHub issues](https://img.shields.io/github/issues/keminze/volo-data)

</div>

<p align="center">
  If this project helps you, please give it a ⭐ Star!
</p>
