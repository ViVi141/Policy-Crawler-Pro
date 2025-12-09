# PostgreSQL 18 with zhparser 中文分词支持
FROM postgres:18-alpine

# 配置 Alpine 镜像源（使用清华大学镜像，加速下载）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

# 安装编译工具和依赖（单层RUN以减小镜像层，添加 wget 用于备用下载）
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    g++ \
    make \
    git \
    wget \
    tar \
    postgresql-dev \
    musl-dev \
    linux-headers \
    && mkdir -p /usr/local/share/postgresql/extension

# 配置 git 使用代理或镜像（如果需要）
# 设置更长的超时时间
RUN git config --global http.postBuffer 524288000 || true && \
    git config --global http.lowSpeedLimit 0 || true && \
    git config --global http.lowSpeedTime 999999 || true

# 下载并编译安装 zhparser（使用多个备用方案，按优先级尝试）
WORKDIR /tmp
RUN set -e; \
    echo "========== 开始下载 zhparser =========="; \
    DOWNLOADED=0; \
    # 方法1: 尝试使用 GitHub 代理下载压缩包（最快） \
    echo "[1/5] 尝试方法1: 使用 GitHub 代理下载压缩包..."; \
    if wget -q --timeout=30 --tries=2 -O zhparser.tar.gz "https://ghproxy.com/https://github.com/amutu/zhparser/archive/refs/heads/master.tar.gz" 2>&1; then \
        echo "✓ 方法1成功：使用 GitHub 代理下载压缩包"; \
        tar -xzf zhparser.tar.gz && mv zhparser-master zhparser && rm -f zhparser.tar.gz && DOWNLOADED=1; \
    # 方法2: 尝试直接从 GitHub 下载压缩包 \
    elif wget -q --timeout=30 --tries=2 -O zhparser.tar.gz "https://github.com/amutu/zhparser/archive/refs/heads/master.tar.gz" 2>&1; then \
        echo "✓ 方法2成功：直接从 GitHub 下载压缩包"; \
        tar -xzf zhparser.tar.gz && mv zhparser-master zhparser && rm -f zhparser.tar.gz && DOWNLOADED=1; \
    # 方法3: 尝试使用 GitHub 代理克隆 \
    elif git clone --depth 1 --branch master "https://ghproxy.com/https://github.com/amutu/zhparser.git" 2>&1; then \
        echo "✓ 方法3成功：使用 GitHub 代理克隆"; \
        DOWNLOADED=1; \
    # 方法4: 尝试直接从 GitHub 克隆 \
    elif git clone --depth 1 --branch master https://github.com/amutu/zhparser.git 2>&1; then \
        echo "✓ 方法4成功：直接从 GitHub 克隆"; \
        DOWNLOADED=1; \
    # 方法5: 最后重试（等待后） \
    else \
        echo "[5/5] 所有方法失败，等待15秒后重试..."; \
        sleep 15; \
        if wget -q --timeout=60 --tries=3 -O zhparser.tar.gz "https://ghproxy.com/https://github.com/amutu/zhparser/archive/refs/heads/master.tar.gz" 2>&1; then \
            echo "✓ 重试成功：使用 GitHub 代理下载压缩包"; \
            tar -xzf zhparser.tar.gz && mv zhparser-master zhparser && rm -f zhparser.tar.gz && DOWNLOADED=1; \
        elif git clone --depth 1 --branch master https://github.com/amutu/zhparser.git 2>&1; then \
            echo "✓ 重试成功：直接从 GitHub 克隆"; \
            DOWNLOADED=1; \
        fi; \
    fi; \
    # 验证下载结果 \
    if [ "$DOWNLOADED" != "1" ] || [ ! -d "zhparser" ]; then \
        echo "❌ 错误: 无法下载 zhparser"; \
        echo "请检查网络连接，或使用 VPN/代理"; \
        echo "您也可以手动下载并放入构建上下文"; \
        exit 1; \
    fi; \
    echo "========== 开始编译 zhparser =========="; \
    cd zhparser && \
    make && \
    make install && \
    cd /tmp && \
    rm -rf zhparser && \
    echo "========== zhparser 安装完成 =========="

# 清理编译工具和缓存（减小镜像大小）
RUN apk del .build-deps \
    && rm -rf /var/cache/apk/* /tmp/* \
    && find /usr/local -name "*.a" -delete \
    && find /usr/local -name "*.la" -delete

# 安装 Python3 用于生成随机密码
RUN apk add --no-cache python3

# 复制包装脚本并设置为 entrypoint
COPY docker-entrypoint-wrapper.sh /usr/local/bin/docker-entrypoint-wrapper.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-wrapper.sh

# 确保扩展目录权限正确
RUN chmod -R 755 /usr/local/share/postgresql/extension

# 设置 entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-wrapper.sh"]

# 设置健康检查
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD pg_isready -U ${POSTGRES_USER:-postgres} || exit 1

WORKDIR /

