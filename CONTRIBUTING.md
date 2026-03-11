# 贡献指南

感谢您对 VoloData 的关注！我们热烈欢迎社区贡献。本文档将指导您如何有效地为项目做出贡献。

## 行为准则

请阅读并遵守我们的 [行为准则](./CODE_OF_CONDUCT.md)。

## 开始贡献

### 报告问题

发现 Bug？请通过 [GitHub Issues](https://github.com/keminze/volo-data/issues) 报告。

**在提交 Issue 前，请：**

1. 检查 Issue 列表中是否已存在类似问题
2. 使用清晰的标题和描述
3. 提供尽可能详细的信息：
   - 环境信息（OS、Python 版本等）
   - 复现步骤
   - 实际结果 vs 预期结果
   - 错误日志和堆栈跟踪

### 提交功能请求

有好点子？欢迎提交功能请求！请：

1. 使用 Issue 讨论您的想法
2. 等待维护者反馈
3. 明确说明用例和预期行为

## 项目结构

```
volo-data/
├── .github/workflows/     # CI 配置
├── config/                # 后端配置
├── routers/               # API 路由
├── services/              # 业务逻辑
├── middlewares/           # 中间件
├── frontend/              # Next.js 前端
│   ├── src/               # 源代码
│   ├── package.json       # 依赖配置
│   └── ...
└── tests/                 # 后端测试
```

## 代码贡献流程

### 1. 环境设置

**后端环境：**

```bash
# Fork 项目到您的账户，然后克隆
git clone https://github.com/keminze/volo-data.git
cd volo-data

# 添加上游远程
git remote add upstream https://github.com/keminze/volo-data.git

# 创建虚拟环境
python -m venv env
source env/bin/activate  # Windows: env\Scripts\activate

# 安装开发依赖
pip install black isort ruff mypy pytest pytest-cov
```

**前端环境：**

```bash
# 进入前端目录
cd frontend

# 安装 Node.js 依赖
npm install
```

### 2. 创建分支

```bash
# 更新主分支
git checkout main
git pull upstream main

# 创建功能分支
git checkout -b feature/your-feature-name
# 或修复分支
git checkout -b fix/issue-number-description
```

**分支命名规范：**

- `feature/` - 新功能
- `fix/` - 问题修复
- `docs/` - 文档更新
- `refactor/` - 代码重构
- `test/` - 测试相关

### 3. 开发

#### 后端代码规范

项目使用以下工具确保代码质量：

| 工具 | 用途 | 检查命令 |
|------|------|----------|
| black | 代码格式化 | `black --check services routers middlewares config` |
| isort | 导入排序 | `isort --check-only services routers middlewares config` |
| ruff | Lint 检查 | `ruff check services routers middlewares config` |
| mypy | 类型检查 | `mypy services routers middlewares config` |

**运行本地检查：**

```bash
# 格式化代码
black services routers middlewares config
isort services routers middlewares config

# 检查代码风格
black --check services routers middlewares config
isort --check-only services routers middlewares config
ruff check services routers middlewares config

# 类型检查
mypy services routers middlewares config
```

#### 前端代码规范

前端使用 Next.js + TypeScript：

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# Lint 检查
npm run lint

# 构建测试
npm run build
```

#### 命名约定

```python
# 函数和变量 - snake_case
def get_user_data():
    user_name = "John"

# 类 - PascalCase
class UserRepository:
    pass

# 常量 - UPPER_SNAKE_CASE
MAX_RETRIES = 3
```

#### 导入顺序

```python
# 标准库
import os
import sys

# 第三方库
from fastapi import FastAPI
from sqlalchemy import create_engine

# 本地导入
from config.database import get_db
from services.user import UserService
```

#### 提交消息规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型：**

- `feat`: 新功能
- `fix`: 问题修复
- `docs`: 文档
- `style`: 格式（无逻辑变更）
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建、依赖更新等

**示例：**

```
feat(api): add new endpoint for data export

Add POST /export endpoint that allows users to export query results
in CSV, JSON, and Excel formats.

Closes #123
```

### 4. 测试

**后端测试：**

```bash
# 运行所有测试
pytest

# 运行特定文件的测试
pytest tests/test_api.py

# 生成覆盖率报告
pytest --cov=. --cov-report=xml --cov-report=term
```

**测试要求：**

- 新功能必须包含单元测试
- 修复 Bug 应该包含测试用例来验证修复
- 代码覆盖率不应低于 80%

### 5. 提交 Pull Request

```bash
# 提交您的更改
git add .
git commit -m "feat(module): description"

# 推送到您的 Fork
git push origin feature/your-feature-name
```

然后在 GitHub 上打开 Pull Request：

1. **标题清晰简洁** - 描述改动内容
2. **详细描述** - 解释为何做出改动、如何测试
3. **关联 Issue** - 使用 `Closes #123` 或 `Fixes #456`
4. **检查清单** - 确保所有项目都完成

#### Pull Request 模板

```markdown
## 描述
<!-- 改动的简要描述 -->

## 类型
- [ ] 新功能
- [ ] 问题修复
- [ ] 重大改变
- [ ] 文档更新

## 关联 Issue
Closes #(issue number)

## 测试方法
<!-- 描述测试步骤 -->

## 检查清单
- [ ] 我的代码遵循项目风格
- [ ] 我进行了自审查
- [ ] 我添加了必要的注释
- [ ] 我添加或更新了相关文档
- [ ] 我的更改不产生新警告
- [ ] 我添加了相关测试
- [ ] 新旧测试都通过了
```

## CI 检查流程

每次提交和 Pull Request 都会自动运行以下检查：

### 后端检查 (Python 3.12)

1. **Lint** - black、isort、ruff 代码风格检查
2. **Type Check** - mypy 类型检查
3. **Test** - pytest 测试 + 覆盖率

### 前端检查 (Node.js 20)

1. **Lint** - npm run lint
2. **Build** - npm run build

确保本地通过所有检查后再提交 PR。

## Review 标准

Pull Request 需要至少一位维护者的审核和批准。

**审核者会检查：**

- 代码质量和一致性
- 测试覆盖率
- 文档完整性
- 性能影响
- 安全性

## 文档贡献

改进文档同样重要！

- 修正拼写和语法错误
- 改进代码示例
- 添加缺失的说明
- 翻译文档

## 讨论和问题

- **讨论**: [GitHub Discussions](https://github.com/keminze/volo-data/discussions)
- **邮件**: kmz3225147671@gmail.com

## 授权

通过向 VoloData 提交代码，您同意您的贡献将根据 Apache 2.0 License 进行授权。

## 感谢

感谢您的贡献！每一个 PR、Issue 报告和代码审查都帮助我们构建更好的软件。