#!/bin/bash
set -e

# 生成随机字符串函数
generate_random_string() {
    local length=$1
    python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#%^&*()-_=+[]{}|;:,.<>?') for _ in range($length)))"
}

# JWT密钥持久化路径（保存在日志卷中）
JWT_KEY_FILE="/app/logs/.jwt_secret_key"

# 如果没有设置 JWT_SECRET_KEY 或者是默认值
if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "change-me-in-production" ]; then
    # 尝试从持久化文件读取
    if [ -f "$JWT_KEY_FILE" ]; then
        export JWT_SECRET_KEY=$(cat "$JWT_KEY_FILE")
        echo "✅ [后端] 从持久化文件读取已有 JWT_SECRET_KEY（容器重启保持一致性）"
    else
        # 首次启动，生成新密钥
        export JWT_SECRET_KEY=$(generate_random_string 128)
        echo "✅ [后端] 首次启动，已自动生成 JWT_SECRET_KEY (128字符)"
        # 保存到持久化文件
        mkdir -p /app/logs
        echo "$JWT_SECRET_KEY" > "$JWT_KEY_FILE"
        chmod 600 "$JWT_KEY_FILE"
        echo "✅ [后端] 已将 JWT_SECRET_KEY 保存到持久化文件: $JWT_KEY_FILE"
    fi
fi

# 如果没有设置 POSTGRES_PASSWORD 或者是默认值，尝试从共享卷读取
if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "mnr_password" ]; then
    # 尝试从共享卷读取数据库自动生成的密码（最多等待10秒）
    max_attempts=10
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if [ -f "/run/secrets/postgres_password" ]; then
            export POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)
            echo "✅ [后端] 已从数据库容器读取 POSTGRES_PASSWORD"
            break
        fi
        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            sleep 1
        fi
    done
    
    if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "mnr_password" ]; then
        echo "⚠️  [后端] 无法从共享卷读取密码，等待数据库容器初始化..."
        echo "⚠️  [后端] 将使用环境变量中的默认值，如果数据库容器已生成密码，连接可能会失败"
        echo "⚠️  [后端] 建议：确保数据库容器已启动并生成密码后再启动后端容器"
    fi
    
    # 更新 DATABASE_URL
    export DATABASE_URL="postgresql://${POSTGRES_USER:-mnr_user}:${POSTGRES_PASSWORD}@${DB_HOST:-db}:${DB_PORT:-5432}/${POSTGRES_DB:-mnr_crawler}"
    echo "✅ [后端] 已更新 DATABASE_URL"
fi

# 显示生成的密钥（仅显示部分，用于调试）
if [ "$DEBUG" = "true" ]; then
    echo "🔑 JWT_SECRET_KEY 前缀: ${JWT_SECRET_KEY:0:20}..."
    echo "🔑 POSTGRES_PASSWORD 前缀: ${POSTGRES_PASSWORD:0:10}..."
fi

# 执行原始命令
exec "$@"
