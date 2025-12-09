# GitHub Actions 工作流快速参考

## 🚀 快速开始

### 1. 推送代码自动构建

每次推送到 `main`、`master` 或 `develop` 分支时，会自动：
- ✅ 构建 Docker 镜像
- ✅ 运行测试
- ✅ 安全扫描
- ✅ 推送到 GitHub Container Registry

### 2. 创建 Release 自动发布

1. 创建 Git 标签：
   ```bash
   git tag -a v3.0.1 -m "Release v3.0.1"
   git push origin v3.0.1
   ```

2. 在 GitHub 上发布 Release：
   - 进入仓库的 `Releases` 页面
   - 点击 `Draft a new release`
   - 选择刚创建的标签
   - 填写 Release 说明
   - 点击 `Publish release`

3. 自动构建并推送带版本标签的镜像

### 3. 查看构建状态

- 进入仓库的 `Actions` 标签页
- 查看各个工作流的运行状态和日志

## 📦 镜像地址

所有镜像发布到：`ghcr.io/vivi141/mnr-law-crawler-online-<service>`

- Backend: `ghcr.io/vivi141/mnr-law-crawler-online-backend`
- Frontend: `ghcr.io/vivi141/mnr-law-crawler-online-frontend`
- Database: `ghcr.io/vivi141/mnr-law-crawler-online-db`

## 🔧 配置 Secrets（可选）

如需启用自动部署，配置以下 Secrets：
- `SSH_HOST` - 服务器地址
- `SSH_USER` - SSH 用户名
- `SSH_PRIVATE_KEY` - SSH 私钥
- `SSH_PORT` - SSH 端口（可选）

## ⚠️ IDE Linter 警告说明

如果您的 IDE（如 VS Code）显示 GitHub Actions 无法解析的警告，这是正常的。这些是 IDE linter 的误报，因为：

1. **GitHub Actions 市场访问限制**：IDE linter 可能无法访问 GitHub Actions 市场
2. **运行时可用**：这些 actions 在 GitHub Actions 运行时是完全可用的
3. **版本正确**：所有使用的 actions 版本都是最新稳定版本

**可以安全忽略这些警告**，工作流在 GitHub 上运行时会正常工作。

## 📚 相关文档

详细配置说明请查看 [.github/README.md](../README.md)
