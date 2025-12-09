#!/bin/sh
# 不在开头使用 set -e，避免小错误导致容器退出
# 启用调试模式，输出所有执行的命令
set -x

echo "=== docker-entrypoint-wrapper.sh 开始执行 ===" >&2

# 生成随机字符串函数
generate_random_string() {
    local length=$1
    python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#%^&*()-_=+[]{}|;:,.<>?') for _ in range($length)))" 2>/dev/null || {
        echo "错误: 无法生成随机密码，请检查 Python3 是否正确安装" >&2
        exit 1
    }
}

# 密码持久化路径（保存在数据卷中，确保重启后不丢失）
PGDATA_DIR="${PGDATA:-/var/lib/postgresql/data}"
PASSWORD_FILE="$PGDATA_DIR/.postgres_password"

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
        
        # 保存密码到持久化文件（确保数据卷目录存在）
        # 注意：不在这里创建 PGDATA 目录，让 PostgreSQL 自己创建
        # 先检查数据卷挂载点是否存在
        PARENT_DIR=$(dirname "$PGDATA_DIR")
        if [ -d "$PARENT_DIR" ]; then
            mkdir -p "$PGDATA_DIR" 2>/dev/null || true
            if echo "$POSTGRES_PASSWORD" > "$PASSWORD_FILE" 2>/dev/null; then
                chmod 600 "$PASSWORD_FILE" 2>/dev/null || true
                echo "✅ [数据库] 已将密码保存到持久化文件: $PASSWORD_FILE" >&2
            else
                echo "⚠️ 警告: 无法立即保存密码文件，将在 PostgreSQL 初始化后保存" >&2
            fi
        else
            echo "⚠️ 警告: 数据目录不存在，密码将在 PostgreSQL 初始化后保存" >&2
        fi
    fi
    
    # 将密码写入共享卷，供其他容器读取（运行时共享）
    mkdir -p /run/secrets 2>/dev/null || true
    echo "$POSTGRES_PASSWORD" > /run/secrets/postgres_password 2>/dev/null || true
    chmod 644 /run/secrets/postgres_password 2>/dev/null || true
    echo "✅ [数据库] 已将密码写入共享卷: /run/secrets/postgres_password" >&2
fi

echo "=== 准备执行 PostgreSQL entrypoint ===" >&2
echo "传递给 entrypoint 的参数: $@" >&2
echo "参数数量: $#" >&2

# 执行原始的 PostgreSQL entrypoint（传递所有参数）
# 在 postgres:18-alpine 中，entrypoint 通常在 /usr/local/bin/docker-entrypoint.sh
# 如果不存在，尝试其他可能的位置
if [ -f /usr/local/bin/docker-entrypoint.sh ]; then
    echo "找到: /usr/local/bin/docker-entrypoint.sh" >&2
    # 如果没有参数，默认传递 'postgres'（PostgreSQL 的默认命令）
    if [ $# -eq 0 ]; then
        echo "警告: 没有参数，使用默认参数 'postgres'" >&2
        exec /usr/local/bin/docker-entrypoint.sh postgres
    else
        exec /usr/local/bin/docker-entrypoint.sh "$@"
    fi
elif [ -f /docker-entrypoint.sh ]; then
    echo "找到: /docker-entrypoint.sh" >&2
    if [ $# -eq 0 ]; then
        exec /docker-entrypoint.sh postgres
    else
        exec /docker-entrypoint.sh "$@"
    fi
else
    echo "搜索 docker-entrypoint.sh..." >&2
    ENTRYPOINT_PATH=$(find / -name "docker-entrypoint.sh" -type f 2>/dev/null | head -1)
    if [ -n "$ENTRYPOINT_PATH" ]; then
        echo "找到: $ENTRYPOINT_PATH" >&2
        if [ $# -eq 0 ]; then
            exec "$ENTRYPOINT_PATH" postgres
        else
            exec "$ENTRYPOINT_PATH" "$@"
        fi
    else
        echo "❌ 错误: 未找到 docker-entrypoint.sh，尝试直接启动 postgres" >&2
        exec postgres "$@"
    fi
fi
