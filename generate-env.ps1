# 生成 .env 文件脚本
# 使用强随机密钥

$ErrorActionPreference = "Stop"

# 生成随机字符串的函数
function Generate-RandomString {
    param([int]$Length)
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#%^&*()-_=+[]{}|;:,.<>?"
    $random = New-Object System.Random
    return -join (1..$Length | ForEach-Object { $chars[$random.Next(0, $chars.Length)] })
}

# 生成密钥
$jwtSecretKey = Generate-RandomString -Length 128
$postgresPassword = Generate-RandomString -Length 32

# 读取模板文件
$templatePath = Join-Path $PSScriptRoot "env.example"
$outputPath = Join-Path $PSScriptRoot ".env"

if (Test-Path $templatePath) {
    $content = Get-Content $templatePath -Raw -Encoding UTF8
    $content = $content -replace 'POSTGRES_PASSWORD=mnr_password', "POSTGRES_PASSWORD=$postgresPassword"
    $content = $content -replace 'JWT_SECRET_KEY=change-me-in-production-please-use-a-random-string', "JWT_SECRET_KEY=$jwtSecretKey"
    $content = $content -replace '# 复制此文件为 .env 并根据实际情况修改配置', '# 自动生成的环境变量配置（包含强随机密钥）'
    Set-Content -Path $outputPath -Value $content -Encoding UTF8 -NoNewline
} else {
    # 如果模板不存在，创建基本配置
    $content = @"
# ============================================
# MNR Law Crawler Online - 环境变量配置
# ============================================
# 自动生成的安全密钥配置

# ============================================
# 数据库配置
# ============================================
POSTGRES_DB=mnr_crawler
POSTGRES_USER=mnr_user
POSTGRES_PASSWORD=$postgresPassword
POSTGRES_PORT=5432

# ============================================
# 后端服务配置
# ============================================
BACKEND_PORT=8000

# JWT认证配置（已生成强随机密钥）
JWT_SECRET_KEY=$jwtSecretKey
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
"@
    Set-Content -Path $outputPath -Value $content -Encoding UTF8
}

Write-Host "✅ .env 文件已生成: $outputPath" -ForegroundColor Green
Write-Host "✅ JWT_SECRET_KEY: $($jwtSecretKey.Substring(0, 20))... (已生成128字符)" -ForegroundColor Green
Write-Host "✅ POSTGRES_PASSWORD: $($postgresPassword.Substring(0, 10))... (已生成32字符)" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  请妥善保管 .env 文件，不要将其提交到 Git 仓库！" -ForegroundColor Yellow
