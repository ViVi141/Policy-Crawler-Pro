#!/bin/sh
set -e

# 生成随机字符串函数
generate_random_string() {
    local length=$1
    python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#%^&*()-_=+[]{}|;:,.<>?') for _ in range($length)))"
}

# 如果没有设置 POSTGRES_PASSWORD 或者是默认值，则生成随机密码
if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "mnr_password" ]; then
    POSTGRES_PASSWORD=$(generate_random_string 32)
    export POSTGRES_PASSWORD
    echo "✅ [数据库] 已自动生成 POSTGRES_PASSWORD (32字符)"
    echo "🔑 [数据库] POSTGRES_PASSWORD 前缀: ${POSTGRES_PASSWORD#?}..." | head -c 50
    
    # 将密码写入共享卷，供其他容器读取
    mkdir -p /run/secrets
    echo "$POSTGRES_PASSWORD" > /run/secrets/postgres_password
    chmod 644 /run/secrets/postgres_password
    echo ""
    echo "✅ [数据库] 已将密码保存到共享卷 /run/secrets/postgres_password"
fi
