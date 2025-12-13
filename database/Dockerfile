# ==============================================================================
# MNR Law Crawler Online - 数据库Docker镜像构建文件
# ==============================================================================
#
# 项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
# 项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
# 作者: ViVi141
# 许可证: MIT License
#
# 描述: 该Dockerfile用于构建PostgreSQL数据库服务的Docker镜像
#       基于PostgreSQL 18，支持自动密码生成和中文分词
#
# ==============================================================================

# PostgreSQL 18
FROM postgres:18-alpine

# 配置 Alpine 镜像源（使用清华大学镜像，加速下载）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories || \
    sed -i'' 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

# 更新包索引并安装 Python3 用于生成随机密码（添加错误处理和重试，支持跨平台构建）
# 注意：在跨平台构建（arm64 QEMU）时，某些 apk trigger 可能失败，需要忽略这些错误
RUN echo "正在更新包索引..." && \
    apk update --no-cache || (sleep 5 && apk update --no-cache) && \
    echo "正在安装 Python3..." && \
    (apk add --no-cache python3 || (echo "Python3 安装失败，重试..." && sleep 5 && apk update --no-cache && apk add --no-cache python3)) && \
    python3 --version && \
    echo "正在安装 pip..." && \
    (apk add --no-cache py3-pip 2>&1; exit 0) | grep -v "trigger" || true && \
    (python3 -m pip --version 2>/dev/null || echo "⚠️ pip 可能未正确安装，但 Python3 可用") && \
    echo "✅ Python3 安装完成"

# 复制 entrypoint wrapper 脚本并确保使用 LF 换行符
COPY docker-entrypoint-wrapper.sh /tmp/docker-entrypoint-wrapper.sh
RUN sed -i'' 's/\r$//' /tmp/docker-entrypoint-wrapper.sh && \
    mv /tmp/docker-entrypoint-wrapper.sh /usr/local/bin/docker-entrypoint-wrapper.sh && \
    chmod +x /usr/local/bin/docker-entrypoint-wrapper.sh

# 复制密码保存脚本（在数据库初始化后执行）
COPY save-password.sh /docker-entrypoint-initdb.d/99-save-password.sh
RUN sed -i'' 's/\r$//' /docker-entrypoint-initdb.d/99-save-password.sh && \
    chmod +x /docker-entrypoint-initdb.d/99-save-password.sh

# 设置执行权限并验证文件
RUN [ -f /usr/local/bin/docker-entrypoint-wrapper.sh ] && \
    [ -x /usr/local/bin/docker-entrypoint-wrapper.sh ] && \
    head -n 1 /usr/local/bin/docker-entrypoint-wrapper.sh | grep -q "#!/bin/sh" && \
    od -c /usr/local/bin/docker-entrypoint-wrapper.sh | head -1 && \
    echo "✅ 验证通过: 文件存在且格式正确"

# 最终验证：确保文件在最终镜像中仍然存在
RUN ls -lh /usr/local/bin/docker-entrypoint-wrapper.sh && \
    [ -f /usr/local/bin/docker-entrypoint-wrapper.sh ] || (echo "❌ 最终验证失败: 文件不存在" && exit 1) && \
    [ -x /usr/local/bin/docker-entrypoint-wrapper.sh ] || (echo "❌ 最终验证失败: 文件不可执行" && exit 1) && \
    echo "✅ 最终验证通过"

# 确保扩展目录权限正确
RUN chmod -R 755 /usr/local/share/postgresql/extension 2>/dev/null || true

# 确保数据目录存在（虽然 Docker 会自动创建，但显式创建更安全）
RUN mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql/data || true

# 设置 entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-wrapper.sh"]

# 默认启动 postgres（显式指定，避免 CMD 为空导致容器退出）
CMD ["postgres"]

# 设置健康检查（与 docker-compose.yml 保持一致）
HEALTHCHECK --interval=10s --timeout=5s --start-period=120s --retries=10 \
    CMD pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-postgres} || exit 1

WORKDIR /
