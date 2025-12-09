# PostgreSQL 18
FROM postgres:18-alpine

# 配置 Alpine 镜像源（使用清华大学镜像，加速下载）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

# 安装 Python3 用于生成随机密码
RUN apk add --no-cache python3

# 复制包装脚本并设置为 entrypoint
COPY docker-entrypoint-wrapper.sh /usr/local/bin/docker-entrypoint-wrapper.sh

# 设置执行权限并验证文件
RUN chmod +x /usr/local/bin/docker-entrypoint-wrapper.sh && \
    test -f /usr/local/bin/docker-entrypoint-wrapper.sh || (echo "错误: docker-entrypoint-wrapper.sh 文件不存在" && exit 1) && \
    head -1 /usr/local/bin/docker-entrypoint-wrapper.sh | grep -q "#!/bin/sh" || (echo "错误: 文件格式不正确" && exit 1)

# 确保扩展目录权限正确
RUN chmod -R 755 /usr/local/share/postgresql/extension

# 设置 entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-wrapper.sh"]

# 设置健康检查
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD pg_isready -U ${POSTGRES_USER:-postgres} || exit 1

WORKDIR /
