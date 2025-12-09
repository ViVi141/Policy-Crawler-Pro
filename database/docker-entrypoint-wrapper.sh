#!/bin/sh
# 不在开头使用 set -e，避免小错误导致容器退出

echo "=== docker-entrypoint-wrapper.sh 开始执行 ===" >&2

# 生成随机字符串函数（使用多种方法确保可靠性）
generate_random_string() {
    local length=$1
    # 方法1: 使用 Python3（首选）
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#%^&*()-_=+[]{}|;:,.<>?') for _ in range($length)))" 2>/dev/null && return 0
    fi
    # 方法2: 使用 /dev/urandom（备用）
    if [ -c /dev/urandom ]; then
        cat /dev/urandom | tr -dc 'a-zA-Z0-9!@#%^&*()-_=+[]{}|;:,.<>?' | fold -w "$length" | head -n 1 && return 0
    fi
    # 方法3: 使用 openssl（备用）
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 "$length" | tr -d '\n' | cut -c1-"$length" && return 0
    fi
    # 如果所有方法都失败，使用简单方法
    echo "警告: 使用简单方法生成密码" >&2
    date +%s | sha256sum | base64 | head -c "$length"
}

# 密码持久化路径（保存在数据卷中，确保重启后不丢失）
# 注意：使用 PGDATA 的父目录来保存密码文件，避免权限问题
PGDATA_DIR="${PGDATA:-/var/lib/postgresql/data}"
PASSWORD_FILE="/var/lib/postgresql/.postgres_password"

# 如果没有设置 POSTGRES_PASSWORD 或者是默认值
if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "mnr_password" ]; then
    # 优先尝试从持久化文件读取密码（即使数据目录不存在，密码文件可能在数据卷中）
    if [ -f "$PASSWORD_FILE" ]; then
        POSTGRES_PASSWORD=$(cat "$PASSWORD_FILE" 2>/dev/null || echo "")
        if [ -n "$POSTGRES_PASSWORD" ]; then
            export POSTGRES_PASSWORD
            echo "✅ [数据库] 从持久化文件读取已有密码（容器重启保持一致性）" >&2
            echo "🔑 [数据库] POSTGRES_PASSWORD 前缀: $(echo $POSTGRES_PASSWORD | cut -c1-10)..." >&2
        fi
    fi
    
    # 如果还是没有密码，生成新密码
    if [ -z "$POSTGRES_PASSWORD" ]; then
        POSTGRES_PASSWORD=$(generate_random_string 32)
        export POSTGRES_PASSWORD
        echo "✅ [数据库] 首次启动，已自动生成 POSTGRES_PASSWORD (32字符)" >&2
        echo "🔑 [数据库] POSTGRES_PASSWORD 前缀: $(echo $POSTGRES_PASSWORD | cut -c1-10)..." >&2
        
        # 注意：不在这里创建 PGDATA 目录或保存密码文件
        # 让 PostgreSQL entrypoint 先完成数据库初始化，然后在初始化完成后保存密码
        # 这样可以避免目录权限问题和初始化冲突
        echo "⚠️ 提示: 密码将在 PostgreSQL 初始化完成后保存" >&2
    fi
    
    # 将密码写入共享卷，供其他容器读取（运行时共享）
    mkdir -p /run/secrets 2>/dev/null || true
    echo "$POSTGRES_PASSWORD" > /run/secrets/postgres_password 2>/dev/null || true
    chmod 644 /run/secrets/postgres_password 2>/dev/null || true
    echo "✅ [数据库] 已将密码写入共享卷: /run/secrets/postgres_password" >&2
fi

echo "=== 准备执行 PostgreSQL entrypoint ===" >&2

# 检查数据目录：如果存在但不完整（缺少 PostgreSQL 版本文件），则清理
if [ -d "$PGDATA_DIR" ]; then
    if [ ! -f "$PGDATA_DIR/PG_VERSION" ]; then
        echo "⚠️ 警告: 数据目录存在但不完整，正在清理..." >&2
        rm -rf "$PGDATA_DIR"/* "$PGDATA_DIR"/.* 2>/dev/null || true
        echo "✅ 数据目录已清理" >&2
    fi
fi

# 执行原始的 PostgreSQL entrypoint（传递所有参数）
# 在 postgres:18-alpine 中，entrypoint 通常在 /usr/local/bin/docker-entrypoint.sh
# 如果不存在，尝试其他可能的位置
if [ -f /usr/local/bin/docker-entrypoint.sh ]; then
    exec /usr/local/bin/docker-entrypoint.sh "$@"
elif [ -f /docker-entrypoint.sh ]; then
    exec /docker-entrypoint.sh "$@"
else
    ENTRYPOINT_PATH=$(find / -name "docker-entrypoint.sh" -type f 2>/dev/null | head -1)
    if [ -n "$ENTRYPOINT_PATH" ]; then
        exec "$ENTRYPOINT_PATH" "$@"
    else
        echo "❌ 错误: 未找到 docker-entrypoint.sh，尝试直接启动 postgres" >&2
        exec postgres "$@"
    fi
fi
