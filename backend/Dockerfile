# ==============================================================================
# MNR Law Crawler Online - 后端Docker镜像构建文件
# ==============================================================================
#
# 项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
# 项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
# 作者: ViVi141
# 许可证: MIT License
#
# 描述: 该Dockerfile用于构建后端服务的Docker镜像
#       采用多阶段构建优化镜像大小，支持清华大学镜像源加速
#
# ==============================================================================

# 构建阶段 - 安装依赖
FROM python:3.12-slim AS builder

WORKDIR /app

# 配置 Debian 镜像源（强制使用清华大学镜像，确保生效）
# 自动检测 Debian 版本以支持多个版本（Debian 11/12/13, Ubuntu 兼容）
RUN set -e; \
    # 检测 Debian 版本代号（支持 bookworm, bullseye, trixie 等） \
    DEBIAN_VERSION=$(cat /etc/os-release 2>/dev/null | grep VERSION_CODENAME | cut -d= -f2 || echo "bookworm") || DEBIAN_VERSION="bookworm"; \
    if [ -z "$DEBIAN_VERSION" ] || [ "$DEBIAN_VERSION" = "" ]; then \
        DEBIAN_VERSION="bookworm"; \
    fi; \
    echo "检测到 Debian 版本: $DEBIAN_VERSION"; \
    # 备份原有配置 \
    mkdir -p /tmp/apt-backup || true; \
    # 重命名 .sources 文件（避免新格式干扰，兼容 Debian 12+） \
    if [ -d /etc/apt/sources.list.d ]; then \
        for f in /etc/apt/sources.list.d/*.sources; do \
            [ -f "$f" ] && mv "$f" "/tmp/apt-backup/$(basename $f)" || true; \
        done 2>/dev/null || true; \
    fi; \
    # 强制创建/覆盖 sources.list（确保使用镜像源，兼容多个 Debian 版本） \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ $DEBIAN_VERSION main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ $DEBIAN_VERSION-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security $DEBIAN_VERSION-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "APT mirror configured: Tsinghua University (Debian $DEBIAN_VERSION)" && \
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

# 升级pip并安装Python依赖（安装到系统位置）
RUN pip install --no-cache-dir --upgrade pip setuptools wheel --timeout=300 --retries=5 && \
    pip install --no-cache-dir -r requirements.txt --timeout=300 --retries=5

# 生产阶段
FROM python:3.12-slim AS production

WORKDIR /app

# 从构建阶段复制已安装的包到系统位置（确保所有用户可访问）
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
RUN chmod -R 755 /usr/local/lib/python3.12/site-packages 2>/dev/null || true && \
    chmod -R 755 /usr/local/bin 2>/dev/null || true

# 配置镜像源（生产阶段，强制使用镜像源，自动检测版本）
RUN set -e; \
    # 检测 Debian 版本代号 \
    DEBIAN_VERSION=$(cat /etc/os-release 2>/dev/null | grep VERSION_CODENAME | cut -d= -f2 || echo "bookworm") || DEBIAN_VERSION="bookworm"; \
    if [ -z "$DEBIAN_VERSION" ] || [ "$DEBIAN_VERSION" = "" ]; then \
        DEBIAN_VERSION="bookworm"; \
    fi; \
    echo "检测到 Debian 版本: $DEBIAN_VERSION"; \
    # 重命名 .sources 文件（避免新格式干扰，兼容 Debian 12+） \
    if [ -d /etc/apt/sources.list.d ]; then \
        for f in /etc/apt/sources.list.d/*.sources; do \
            [ -f "$f" ] && mv "$f" "$f.bak" || true; \
        done 2>/dev/null || true; \
    fi; \
    # 强制覆盖 sources.list（兼容多个 Debian 版本） \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ $DEBIAN_VERSION main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ $DEBIAN_VERSION-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security $DEBIAN_VERSION-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list || true

# 安装运行时依赖（包括 LibreOffice 用于 DOC 转 DOCX）
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    libreoffice \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 复制应用代码
COPY --chown=appuser:appuser . .

# 处理 entrypoint 脚本的 Windows CRLF 换行符问题（确保脚本可执行）
RUN if [ -f /app/docker-entrypoint.sh ]; then \
        tr -d '\r' < /app/docker-entrypoint.sh > /app/docker-entrypoint.sh.tmp && \
        mv /app/docker-entrypoint.sh.tmp /app/docker-entrypoint.sh && \
        chmod +x /app/docker-entrypoint.sh && \
        chown appuser:appuser /app/docker-entrypoint.sh; \
    fi

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/usr/local/bin:$PATH \
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
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

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
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

