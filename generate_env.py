#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MNR Law Crawler Online - 环境变量生成脚本 (Python)
# ==============================================================================
#
# 项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
# 项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
# 作者: ViVi141
# 许可证: MIT License
#
# 描述: 该脚本用于自动生成包含强随机密钥的环境变量配置文件
#       支持自动生成数据库密码和JWT密钥，确保生产环境的安全性
#
# 使用方法:
#   python generate_env.py
#
# ==============================================================================

"""
生成 .env 文件，包含强随机密钥
"""
import secrets
import string
from pathlib import Path


def generate_random_string(length: int) -> str:
    """生成强随机字符串"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # 移除可能造成问题的特殊字符
    alphabet = (
        alphabet.replace('"', "")
        .replace("'", "")
        .replace("$", "")
        .replace("\\", "")
        .replace("`", "")
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_env_file():
    """生成 .env 文件"""
    env_file = Path(__file__).parent / ".env"

    # 生成随机密钥
    jwt_secret_key = generate_random_string(128)  # JWT密钥需要足够长
    postgres_password = generate_random_string(32)  # 数据库密码

    # 读取模板
    example_file = Path(__file__).parent / "env.example"
    if example_file.exists():
        content = example_file.read_text(encoding="utf-8")
        # 替换密钥
        content = content.replace(
            "POSTGRES_PASSWORD=mnr_password", f"POSTGRES_PASSWORD={postgres_password}"
        )
        content = content.replace(
            "JWT_SECRET_KEY=change-me-in-production-please-use-a-random-string",
            f"JWT_SECRET_KEY={jwt_secret_key}",
        )
        # 更新注释
        content = content.replace(
            "# 复制此文件为 .env 并根据实际情况修改配置",
            "# 自动生成的环境变量配置（包含强随机密钥）",
        )
    else:
        # 如果模板不存在，创建基本配置
        content = f"""# ============================================
# MNR Law Crawler Online - 环境变量配置
# ============================================
# 自动生成的安全密钥配置

# ============================================
# 数据库配置
# ============================================
POSTGRES_DB=mnr_crawler
POSTGRES_USER=mnr_user
POSTGRES_PASSWORD={postgres_password}
POSTGRES_PORT=5432

# ============================================
# 后端服务配置
# ============================================
BACKEND_PORT=8000

# JWT认证配置（已生成强随机密钥）
JWT_SECRET_KEY={jwt_secret_key}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 应用配置
DEBUG=false
LOG_LEVEL=INFO

# ============================================
# 前端服务配置
# ============================================
FRONTEND_PORT=3000
VITE_API_BASE_URL=http://localhost:8000

# ============================================
# 存储配置
# ============================================
STORAGE_MODE=local
STORAGE_LOCAL_DIR=./crawled_data

# S3存储配置（可选）
S3_ENABLED=false
S3_PROVIDER=aws
S3_BUCKET_NAME=
S3_REGION=us-east-1
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=

# ============================================
# 缓存配置
# ============================================
CACHE_ENABLED=true
CACHE_DIR=./cache
CACHE_TTL_SECONDS=86400
CACHE_MAX_SIZE_GB=10

# ============================================
# 邮件服务配置（可选）
# ============================================
EMAIL_ENABLED=false
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-email@example.com
EMAIL_SMTP_PASSWORD=your-email-password
EMAIL_FROM_ADDRESS=your-email@example.com
EMAIL_TO_ADDRESSES=["admin@example.com"]

# ============================================
# 定时任务配置
# ============================================
SCHEDULER_ENABLED=true

# ============================================
# CORS配置
# ============================================
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# ============================================
# 日志配置
# ============================================
LOG_FILE=./logs/app.log
"""

    # 写入文件
    env_file.write_text(content, encoding="utf-8")
    print(f"✅ .env 文件已生成: {env_file}")
    print(f"✅ JWT_SECRET_KEY: {jwt_secret_key[:20]}... (已生成128字符)")
    print(f"✅ POSTGRES_PASSWORD: {postgres_password[:10]}... (已生成32字符)")
    print("\n⚠️  请妥善保管 .env 文件，不要将其提交到 Git 仓库！")


if __name__ == "__main__":
    generate_env_file()
