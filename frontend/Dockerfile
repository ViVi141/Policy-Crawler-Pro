# ==============================================================================
# MNR Law Crawler Online - 前端Docker镜像构建文件
# ==============================================================================
#
# 项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
# 项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
# 作者: ViVi141
# 许可证: MIT License
#
# 描述: 该Dockerfile用于构建前端服务的Docker镜像
#       采用多阶段构建，配置国内镜像源加速构建过程
#
# ==============================================================================

# 构建阶段
FROM node:24-alpine AS builder

# 配置 Alpine 镜像源（使用清华大学镜像，加速下载）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

WORKDIR /app

# 配置 npm 镜像源（使用淘宝镜像，加速下载）
RUN npm config set registry https://registry.npmmirror.com

# 安装构建依赖（使用缓存层优化）
COPY package.json package-lock.json* ./

# 升级npm并安装依赖（使用npm ci确保依赖一致性，添加超时和重试）
RUN set -e; \
    echo "正在升级 npm..."; \
    npm install -g npm@latest --timeout=300000 || (echo "npm 升级失败，使用现有版本" && npm --version); \
    echo "正在安装依赖..."; \
    npm ci --legacy-peer-deps --prefer-offline --no-audit --timeout=300000 || \
    (echo "npm ci 失败，尝试使用 npm install..." && npm install --legacy-peer-deps --prefer-offline --no-audit --timeout=300000); \
    echo "依赖安装完成"

# 复制源代码（在依赖安装后，优化构建缓存）
COPY . .

# 构建参数
# 使用相对路径（空字符串），通过Nginx代理访问后端
# 前端代码使用相对路径 /api/xxx，Nginx将代理到 Docker网络中的 backend:8000
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# 构建应用
RUN npm run build

# 运行阶段 - 使用更小的nginx镜像
FROM nginx:1.29-alpine

# 配置 Alpine 镜像源（使用清华大学镜像，加速下载）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

# 安装必要的工具用于健康检查
RUN apk add --no-cache curl

# 创建nginx用户和组（如果不存在）
RUN addgroup -g 101 -S nginx || true && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx || true

# 复制构建结果
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# 创建自定义nginx主配置文件（覆盖默认配置，设置PID文件路径）
RUN echo 'pid /var/cache/nginx/nginx.pid;' > /tmp/nginx_custom.conf && \
    cat /etc/nginx/nginx.conf | grep -v "^pid " >> /tmp/nginx_custom.conf && \
    mv /tmp/nginx_custom.conf /etc/nginx/nginx.conf && \
    chown root:root /etc/nginx/nginx.conf

# 创建必要的目录并设置权限（包括 /run 目录用于 PID 文件）
RUN mkdir -p /var/cache/nginx /var/log/nginx /etc/nginx/conf.d /run && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /usr/share/nginx/html /run && \
    chmod -R 755 /usr/share/nginx/html && \
    chmod 755 /run

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

EXPOSE 80

# 使用非root用户运行nginx
USER nginx

CMD ["nginx", "-g", "daemon off;"]

