# GitHub Actions CI/CD 配置说明

本项目使用 GitHub Actions 实现持续集成和持续部署（CI/CD）。

## 📋 工作流说明

### 1. CI/CD Pipeline (`.github/workflows/ci.yml`)

**触发条件**:
- 推送到 `main`、`master` 或 `develop` 分支
- 创建 Pull Request
- 发布 Release

**执行任务**:
- ✅ 构建并推送 Docker 镜像到 GitHub Container Registry
- ✅ 运行后端测试
- ✅ 运行前端测试和构建
- ✅ 安全漏洞扫描（Trivy）
- ✅ 代码质量检查

**镜像标签**:
- `latest` - 默认分支的最新版本
- `main-<sha>` - 基于 commit SHA 的标签
- `v<version>` - Release 版本标签

### 2. Docker Compose Build Test (`.github/workflows/docker-compose.yml`)

**触发条件**:
- 推送到 `main`、`master` 或 `develop` 分支
- 创建 Pull Request

**执行任务**:
- ✅ 使用 docker-compose 构建所有服务
- ✅ 启动所有容器
- ✅ 健康检查验证

### 3. Release (`.github/workflows/release.yml`)

**触发条件**:
- 发布 GitHub Release
- 手动触发（workflow_dispatch）

**执行任务**:
- ✅ 构建并推送带版本标签的镜像
- ✅ 生成 Release 说明

### 4. Deploy (`.github/workflows/deploy.yml`)

**触发条件**:
- CI/CD Pipeline 成功完成后
- 手动触发

**执行任务**:
- ✅ 部署到服务器（需要配置 SSH 密钥）

## 🔧 配置说明

### GitHub Secrets 配置

如需启用自动部署，需要在 GitHub 仓库设置中添加以下 Secrets：

1. **SSH_HOST** - 服务器 IP 地址或域名
2. **SSH_USER** - SSH 用户名
3. **SSH_PRIVATE_KEY** - SSH 私钥
4. **SSH_PORT** - SSH 端口（可选，默认 22）

### 配置步骤

1. 进入 GitHub 仓库
2. 点击 `Settings` → `Secrets and variables` → `Actions`
3. 点击 `New repository secret`
4. 添加上述 Secrets

### 使用 GitHub Container Registry

镜像会自动推送到 GitHub Container Registry，格式为：
```
ghcr.io/<username>/mnr-law-crawler-online-<service>:<tag>
```

**拉取镜像**（需要登录）:
```bash
# 登录到 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 拉取镜像
docker pull ghcr.io/vivi141/mnr-law-crawler-online-backend:latest
docker pull ghcr.io/vivi141/mnr-law-crawler-online-frontend:latest
docker pull ghcr.io/vivi141/mnr-law-crawler-online-db:latest
```

**公开镜像**:
1. 进入 GitHub 仓库的 `Packages` 页面
2. 选择对应的镜像包
3. 点击 `Package settings` → `Change visibility` → `Public`

## 🚀 使用流程

### 开发流程

1. **创建分支并开发**
   ```bash
   git checkout -b feature/new-feature
   # 进行开发...
   git commit -m "Add new feature"
   git push origin feature/new-feature
   ```

2. **创建 Pull Request**
   - GitHub 会自动运行 CI/CD Pipeline
   - 检查构建和测试结果
   - 代码审查通过后合并

3. **合并到主分支**
   - 自动触发构建和测试
   - 镜像推送到 GitHub Container Registry

### 发布流程

1. **创建 Release**
   ```bash
   git tag -a v3.0.1 -m "Release version 3.0.1"
   git push origin v3.0.1
   ```

2. **在 GitHub 上发布 Release**
   - 进入 `Releases` 页面
   - 点击 `Draft a new release`
   - 选择标签并填写 Release 说明
   - 点击 `Publish release`

3. **自动构建和推送**
   - Release 工作流会自动运行
   - 构建并推送带版本标签的镜像
   - 生成 Release 说明

## 📊 工作流状态

可以在以下位置查看工作流状态：

- GitHub 仓库的 `Actions` 标签页
- README.md 中的状态徽章（需要添加）

## 🔍 故障排查

### 构建失败

1. **检查日志**: 在 GitHub Actions 页面查看详细日志
2. **本地测试**: 在本地运行相同的构建命令
3. **检查依赖**: 确保所有依赖都已正确配置

### 镜像推送失败

1. **检查权限**: 确保 GitHub Token 有推送权限
2. **检查仓库设置**: 确保 Container Registry 已启用
3. **检查镜像名称**: 确保镜像名称符合规范

### 部署失败

1. **检查 SSH 配置**: 确保 SSH 密钥和主机配置正确
2. **检查服务器状态**: 确保服务器可访问
3. **检查部署脚本**: 确保部署路径和命令正确

## 📝 自定义配置

### 修改构建平台

在 `ci.yml` 中修改 `platforms` 参数：
```yaml
platforms: linux/amd64,linux/arm64,linux/arm/v7
```

### 添加测试

在 `ci.yml` 的 `test-backend` 或 `test-frontend` job 中添加测试命令。

### 修改部署目标

在 `deploy.yml` 中修改部署脚本和服务器配置。

## 🔐 安全建议

1. **使用 Secrets**: 不要在代码中硬编码敏感信息
2. **最小权限**: 只授予必要的权限
3. **定期更新**: 定期更新 Actions 版本
4. **安全扫描**: 启用 Dependabot 和安全扫描

## 📚 相关资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Docker Buildx 文档](https://docs.docker.com/buildx/)
- [GitHub Container Registry 文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
