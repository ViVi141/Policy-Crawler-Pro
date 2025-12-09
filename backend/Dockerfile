# 构建阶段 - 安装依赖
FROM python:3.12.10-slim AS builder

WORKDIR /app

# 配置 Debian 镜像源（强制使用清华大学镜像，确保生效）
# Debian 12 使用新的 deb822 格式，需要同时处理 .sources 和 sources.list
RUN set -e; \
    # 备份原有配置 \
    mkdir -p /tmp/apt-backup || true; \
    # 重命名 .sources 文件（避免新格式干扰） \
    if [ -d /etc/apt/sources.list.d ]; then \
        for f in /etc/apt/sources.list.d/*.sources; do \
            [ -f "$f" ] && mv "$f" "/tmp/apt-backup/$(basename $f)" || true; \
        done 2>/dev/null || true; \
    fi; \
    # 强制创建/覆盖 sources.list（确保使用镜像源） \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "APT mirror configured: Tsinghua University" && \
    echo "=== Current sources.list ===" && \
    cat /etc/apt/sources.list

# 安装构建依赖（添加重试机制和超时设置）
RUN set -e; \
    echo "正在更新软件包列表..."; \
    apt-get update --fix-missing || (sleep 5 && apt-get update --fix-missing); \
    echo "正在安装构建依赖..."; \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    || (echo "安装失败，等待后重试..." && sleep 10 && apt-get update --fix-missing && \
        apt-get install -y --no-install-recommends gcc g++ postgresql-client); \
    rm -rf /var/lib/apt/lists/* && \
    echo "构建依赖安装完成"

# 复制依赖文件
COPY requirements.txt .

# 配置 pip 镜像源（使用清华大学镜像，加速下载）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple || true

# 升级pip并安装Python依赖（使用缓存层优化，添加超时和重试）
RUN pip install --no-cache-dir --upgrade pip setuptools wheel --timeout=300 --retries=5 && \
    pip install --no-cache-dir --user -r requirements.txt --timeout=300 --retries=5

# 生产阶段
FROM python:3.12.10-slim AS production

WORKDIR /app

# 从构建阶段复制已安装的包
COPY --from=builder /root/.local /root/.local

# 配置镜像源（生产阶段，强制使用镜像源）
RUN set -e; \
    # 重命名 .sources 文件（避免新格式干扰） \
    if [ -d /etc/apt/sources.list.d ]; then \
        for f in /etc/apt/sources.list.d/*.sources; do \
            [ -f "$f" ] && mv "$f" "$f.bak" || true; \
        done 2>/dev/null || true; \
    fi; \
    # 强制覆盖 sources.list \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list || true

# 安装运行时依赖
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 复制应用代码
COPY --chown=appuser:appuser . .

# 复制并设置 entrypoint 脚本
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1

# 切换到非root用户
USER appuser

# 创建必要的目录
RUN mkdir -p /app/cache /app/crawled_data /app/logs

# 设置 entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 健康检查（使用Python而不是curl，更可靠）
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health').read()" || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# 开发阶段（可选，用于开发环境）
FROM production AS development

USER root

# 安装开发工具
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 切换回appuser
USER appuser

# 开发模式使用reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

