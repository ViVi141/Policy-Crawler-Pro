# PostgreSQL 18 with zhparser 中文分词支持
FROM postgres:18-alpine

# 配置 Alpine 镜像源（使用清华大学镜像，加速下载）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

# 安装编译工具和依赖（单层RUN以减小镜像层，添加重试）
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    g++ \
    make \
    git \
    postgresql-dev \
    musl-dev \
    linux-headers \
    && mkdir -p /usr/local/share/postgresql/extension

# 下载并编译安装 zhparser（使用缓存优化，添加重试和超时）
WORKDIR /tmp
RUN git clone --depth 1 --branch master https://github.com/amutu/zhparser.git || \
    (sleep 5 && git clone --depth 1 --branch master https://github.com/amutu/zhparser.git) && \
    cd zhparser && \
    make && \
    make install && \
    cd .. && \
    rm -rf zhparser

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

