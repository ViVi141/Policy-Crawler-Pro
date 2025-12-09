#!/bin/sh
set -e

# 生成随机字符串函数
generate_random_string() {
    local length=$1
    python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#%^&*()-_=+[]{}|;:,.<>?') for _ in range($length)))"
}

# 密码持久化路径（保存在数据卷中，确保重启后不丢失）
PGDATA_DIR="${PGDATA:-/var/lib/postgresql/data}"
PASSWORD_FILE="$PGDATA_DIR/.postgres_password"

# 如果没有设置 POSTGRES_PASSWORD 或者是默认值
if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "mnr_password" ]; then
    # 优先尝试从持久化文件读取密码（即使数据目录不存在，密码文件可能在数据卷中）
    if [ -f "$PASSWORD_FILE" ]; then
        POSTGRES_PASSWORD=$(cat "$PASSWORD_FILE")
        export POSTGRES_PASSWORD
        echo "✅ [数据库] 从持久化文件读取已有密码（容器重启保持一致性）"
        echo "🔑 [数据库] POSTGRES_PASSWORD 前缀: $(echo $POSTGRES_PASSWORD | cut -c1-10)..."
    else
        # 持久化文件不存在，生成新密码
        POSTGRES_PASSWORD=$(generate_random_string 32)
        export POSTGRES_PASSWORD
        echo "✅ [数据库] 首次启动，已自动生成 POSTGRES_PASSWORD (32字符)"
        echo "🔑 [数据库] POSTGRES_PASSWORD 前缀: $(echo $POSTGRES_PASSWORD | cut -c1-10)..."
        
        # 保存密码到持久化文件（确保数据卷目录存在）
        mkdir -p "$PGDATA_DIR"
        echo "$POSTGRES_PASSWORD" > "$PASSWORD_FILE"
        chmod 600 "$PASSWORD_FILE"
        echo "✅ [数据库] 已将密码保存到持久化文件: $PASSWORD_FILE"
    fi
    
    # 将密码写入共享卷，供其他容器读取（运行时共享）
    mkdir -p /run/secrets
    echo "$POSTGRES_PASSWORD" > /run/secrets/postgres_password
    chmod 644 /run/secrets/postgres_password
    echo "✅ [数据库] 已将密码写入共享卷: /run/secrets/postgres_password"
fi

# 执行原始的 PostgreSQL entrypoint（传递所有参数）
exec /usr/local/bin/docker-entrypoint.sh "$@"
