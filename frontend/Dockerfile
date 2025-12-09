# 构建阶段
FROM node:24-alpine AS builder

WORKDIR /app

# 安装构建依赖（使用缓存层优化）
COPY package.json package-lock.json* ./

# 升级npm并安装依赖（使用npm ci确保依赖一致性）
RUN npm install -g npm@latest && \
    npm ci --legacy-peer-deps --prefer-offline --no-audit

# 复制源代码（在依赖安装后，优化构建缓存）
COPY . .

# 构建参数
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# 构建应用
RUN npm run build

# 运行阶段 - 使用更小的nginx镜像
FROM nginx:1.27-alpine

# 安装必要的工具用于健康检查
RUN apk add --no-cache curl

# 创建nginx用户和组（如果不存在）
RUN addgroup -g 101 -S nginx || true && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx || true

# 复制构建结果
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# 创建必要的目录并设置权限
RUN mkdir -p /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

EXPOSE 80

# 使用非root用户运行nginx
USER nginx

CMD ["nginx", "-g", "daemon off;"]

