# PostgreSQL 18
FROM postgres:18-alpine

# 配置 Alpine 镜像源（使用清华大学镜像，加速下载）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

# 安装 Python3 用于生成随机密码
RUN apk add --no-cache python3

# 复制包装脚本并设置为 entrypoint
# 注意：构建上下文是 ./database，所以这里直接使用文件名
COPY docker-entrypoint-wrapper.sh /usr/local/bin/docker-entrypoint-wrapper.sh

# 设置执行权限并验证文件（添加详细的调试信息）
RUN echo "=== 开始验证文件 ===" && \
    ls -lah /usr/local/bin/docker-entrypoint-wrapper.sh && \
    file /usr/local/bin/docker-entrypoint-wrapper.sh && \
    chmod +x /usr/local/bin/docker-entrypoint-wrapper.sh && \
    test -f /usr/local/bin/docker-entrypoint-wrapper.sh || (echo "❌ 错误: docker-entrypoint-wrapper.sh 文件不存在" && echo "当前目录文件列表:" && ls -la /usr/local/bin/ && exit 1) && \
    head -1 /usr/local/bin/docker-entrypoint-wrapper.sh | grep -q "#!/bin/sh" || (echo "❌ 错误: 文件格式不正确" && head -5 /usr/local/bin/docker-entrypoint-wrapper.sh && exit 1) && \
    echo "✅ 验证通过: 文件存在且格式正确" && \
    cat /usr/local/bin/docker-entrypoint-wrapper.sh | head -5

# 确保扩展目录权限正确
RUN chmod -R 755 /usr/local/share/postgresql/extension 2>/dev/null || true

# 设置 entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-wrapper.sh"]

# 设置健康检查
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD pg_isready -U ${POSTGRES_USER:-postgres} || exit 1

WORKDIR /
