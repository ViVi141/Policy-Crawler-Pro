# PostgreSQL 18
FROM postgres:18-alpine

# 配置 Alpine 镜像源（使用清华大学镜像，加速下载）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

# 安装 Python3 用于生成随机密码
RUN apk add --no-cache python3

# 直接使用 echo 创建 entrypoint 脚本（避免 COPY 可能的问题）
RUN echo '#!/bin/sh' > /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '# 生成随机字符串函数' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'generate_random_string() {' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    local length=$1' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    python3 -c "import secrets, string; print('"'"''"'"'.join(secrets.choice(string.ascii_letters + string.digits + '"'"'!@#%^&*()-_=+[]{}|;:,.<>?'"'"') for _ in range($length)))" 2>/dev/null || {' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        echo "错误: 无法生成随机密码"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        exit 1' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    }' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '}' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'PGDATA_DIR="${PGDATA:-/var/lib/postgresql/data}"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'PASSWORD_FILE="$PGDATA_DIR/.postgres_password"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "mnr_password" ]; then' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    if [ -f "$PASSWORD_FILE" ]; then' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        POSTGRES_PASSWORD=$(cat "$PASSWORD_FILE" 2>/dev/null || echo "")' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        if [ -n "$POSTGRES_PASSWORD" ]; then' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '            export POSTGRES_PASSWORD' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '            echo "✅ [数据库] 从持久化文件读取已有密码"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        fi' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    fi' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    if [ -z "$POSTGRES_PASSWORD" ]; then' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        POSTGRES_PASSWORD=$(generate_random_string 32)' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        export POSTGRES_PASSWORD' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        echo "✅ [数据库] 首次启动，已自动生成 POSTGRES_PASSWORD (32字符)"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        PARENT_DIR=$(dirname "$PGDATA_DIR")' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        if [ -d "$PARENT_DIR" ]; then' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '            mkdir -p "$PGDATA_DIR" 2>/dev/null || true' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '            echo "$POSTGRES_PASSWORD" > "$PASSWORD_FILE" 2>/dev/null || true' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '            chmod 600 "$PASSWORD_FILE" 2>/dev/null || true' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        fi' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    fi' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    mkdir -p /run/secrets 2>/dev/null || true' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    echo "$POSTGRES_PASSWORD" > /run/secrets/postgres_password 2>/dev/null || true' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    chmod 644 /run/secrets/postgres_password 2>/dev/null || true' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'fi' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'if [ -f /usr/local/bin/docker-entrypoint.sh ]; then' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    exec /usr/local/bin/docker-entrypoint.sh "$@"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'elif [ -f /docker-entrypoint.sh ]; then' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    exec /docker-entrypoint.sh "$@"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'else' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    ENTRYPOINT_PATH=$(find / -name "docker-entrypoint.sh" -type f 2>/dev/null | head -1)' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    if [ -n "$ENTRYPOINT_PATH" ]; then' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        exec "$ENTRYPOINT_PATH" "$@"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    else' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '        exec postgres "$@"' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo '    fi' >> /usr/local/bin/docker-entrypoint-wrapper.sh && \
    echo 'fi' >> /usr/local/bin/docker-entrypoint-wrapper.sh

# 设置执行权限并验证文件
RUN chmod +x /usr/local/bin/docker-entrypoint-wrapper.sh && \
    [ -f /usr/local/bin/docker-entrypoint-wrapper.sh ] && \
    [ -x /usr/local/bin/docker-entrypoint-wrapper.sh ] && \
    head -n 1 /usr/local/bin/docker-entrypoint-wrapper.sh | grep -q "#!/bin/sh" && \
    echo "✅ 验证通过: 文件存在且格式正确"

# 最终验证：确保文件在最终镜像中仍然存在
RUN ls -lh /usr/local/bin/docker-entrypoint-wrapper.sh && \
    [ -f /usr/local/bin/docker-entrypoint-wrapper.sh ] || (echo "❌ 最终验证失败: 文件不存在" && exit 1) && \
    [ -x /usr/local/bin/docker-entrypoint-wrapper.sh ] || (echo "❌ 最终验证失败: 文件不可执行" && exit 1) && \
    echo "✅ 最终验证通过"

# 确保扩展目录权限正确
RUN chmod -R 755 /usr/local/share/postgresql/extension 2>/dev/null || true

# 设置 entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-wrapper.sh"]

# 设置健康检查
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD pg_isready -U ${POSTGRES_USER:-postgres} || exit 1

WORKDIR /
