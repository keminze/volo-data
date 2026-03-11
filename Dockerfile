# 建议使用 slim-bookworm，它基于稳定的 Debian 12，比默认镜像更轻且稳定
FROM python:3.12-slim

# 设置环境变量
# PYTHONUNBUFFERED: 实时输出日志，方便调试崩溃
# PIP_NO_CACHE_DIR: 禁用缓存，大幅减少内存占用
# PIP_DEFAULT_TIMEOUT: 防止弱网或 CPU 繁忙导致的下载超时
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    DENO_INSTALL="/root/.deno" \
    PATH="/root/.deno/bin:$PATH"

WORKDIR /app

# 分开安装系统依赖，并清理缓存
# 增加 --fix-missing 并限制并发
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl unzip && \
    curl -fsSL https://deno.land/install.sh | sh && \
    apt-get purge -y --auto-remove curl unzip && \
    rm -rf /var/lib/apt/lists/*

# RUN python -m pip install langchain-sandbox --no-cache-dir

# 复制依赖文件
COPY requirements.txt ./

# 优化 pip 安装
# 1. 升级 pip
# 2. 强制使用单线程安装 (--jobs 1)，这是防止 Segfault 的关键，降低 CPU 负载
# 3. 如果 greenlet 依然崩，加上 --no-binary greenlet
RUN python -m pip install --upgrade pip --root-user-action=ignore && \
    python -m pip install -r requirements.txt \
    --no-cache-dir \
    --no-compile

# 复制项目文件
COPY . .

# 优化本地项目的安装
# 使用 --no-deps 避免重新检查已经安装过的依赖
# RUN if [ -d "llm-sandbox" ]; then \
#     cd llm-sandbox && pip install -e . --no-deps; \
#     fi

# RUN mkdir logs

# 暴露端口
EXPOSE 9000

# 确保 entrypoint.sh 具有执行权限
RUN chmod +x /app/entrypoint.sh

# 暴露端口
EXPOSE 9000

# 使用 ENTRYPOINT
ENTRYPOINT ["/app/entrypoint.sh"]

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "1"]