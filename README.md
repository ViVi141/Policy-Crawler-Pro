# MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)

> **Web化政策法规库管理系统** - 集爬取、存储、搜索、管理于一体的现代化政策法规库系统

**English**: MNR Law Crawler Online | **中文**: 自然资源部法规爬虫系统（Web版）

## 📌 项目说明

这是一个全新的Web应用项目，用于管理和爬取自然资源部政策法规数据。项目采用了现代化的前后端分离架构，提供了完整的政策法规库管理功能。

> **注意**：本项目的爬虫核心逻辑来自原 [mnr-law-crawler](https://github.com/ViVi141/mnr-law-crawler) 项目，但整体架构、功能设计和实现都是全新的。

## ✨ 核心特性

### 🌐 Web化系统
- 🎨 **现代化前端**：Vue 3 + TypeScript + Element Plus 构建的美观Web界面
- 🚀 **RESTful API**：FastAPI 构建的高性能后端服务
- 📱 **响应式设计**：支持不同屏幕尺寸，良好的移动端体验
- 🔐 **安全认证**：JWT Token认证，安全的用户管理

### 🕷️ 智能爬虫
- 🎯 **多数据源支持**：支持政府信息公开平台、政策法规库等多个数据源
- 🔄 **智能解析**：针对不同数据源使用专用HTML解析器
- ⏱️ **时间范围过滤**：支持指定日期范围进行增量爬取
- 🔍 **关键词搜索**：支持关键词筛选，或全量爬取
- ⚡ **可配置延迟**：支持设置请求延迟，避免对目标服务器造成压力
- 🛡️ **容错机制**：自动重试失败的政策，完善的错误处理

### 📚 政策库管理
- 💾 **多格式存储**：自动保存JSON、Markdown、DOCX和原始文件
- 🔍 **全文搜索**：基于PostgreSQL的全文搜索，支持关键词、分类、日期等多维度筛选
- 📊 **数据统计**：实时显示政策数量、任务进度等统计信息
- 🏷️ **分类管理**：自动提取和分类政策，支持按分类筛选
- 📎 **附件管理**：自动下载和管理政策附件

### ⚙️ 任务管理
- 🎮 **任务创建**：灵活的任务配置（关键词、日期范围、数据源选择、页面限制）
- 📈 **实时监控**：实时显示任务执行进度和统计信息
- ⏸️ **任务控制**：支持启动、取消任务
- 📝 **任务历史**：完整的任务执行历史记录
- 🔔 **邮件通知**：任务完成/失败自动邮件通知（可选）

### 🕐 定时任务
- ⏰ **Cron支持**：支持Cron表达式配置定时任务
- 📅 **灵活调度**：支持启用/禁用定时任务
- 📊 **执行历史**：查看定时任务的执行历史记录

### ☁️ 存储与备份
- 💿 **本地存储**：默认使用本地文件系统存储
- ☁️ **S3存储**：可选配置AWS S3或兼容的对象存储服务
- 💾 **数据库备份**：支持PostgreSQL数据库备份和恢复
- 🔄 **自动清理**：支持清理旧文件和备份

### 🎛️ 系统配置
- 🔧 **功能开关**：灵活的功能开关管理
- 📧 **邮件配置**：支持SMTP邮件服务配置
- 🗄️ **数据源管理**：可视化配置和管理多个数据源
- ⚙️ **爬虫配置**：可配置请求延迟、代理设置等

## 🏗️ 技术架构

### 前端技术栈
- **框架**：Vue 3 (Composition API)
- **语言**：TypeScript
- **状态管理**：Pinia
- **路由**：Vue Router
- **UI组件**：Element Plus
- **HTTP客户端**：Axios
- **构建工具**：Vite

### 后端技术栈
- **框架**：FastAPI
- **语言**：Python 3.11+
- **ORM**：SQLAlchemy
- **数据库**：PostgreSQL
- **认证**：JWT (JSON Web Tokens)
- **任务调度**：APScheduler
- **文档转换**：python-docx, mammoth
- **HTML解析**：BeautifulSoup4

### 存储方案
- **元数据**：PostgreSQL
- **文件存储**：本地文件系统 或 AWS S3
- **缓存**：本地文件缓存

## 📦 项目结构

```
MNR-Law-Crawler-Online/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心爬虫逻辑
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic模型
│   │   ├── services/       # 业务服务层
│   │   ├── middleware/     # 中间件
│   │   └── main.py         # FastAPI应用入口
│   ├── migrations/         # 数据库迁移
│   ├── requirements.txt    # Python依赖
│   └── Dockerfile          # Docker镜像
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── api/           # API客户端
│   │   ├── views/         # 页面组件
│   │   ├── layouts/       # 布局组件
│   │   ├── stores/        # 状态管理
│   │   ├── router/        # 路由配置
│   │   └── types/         # TypeScript类型
│   ├── package.json       # Node.js依赖
│   └── Dockerfile         # Docker镜像
├── docker-compose.yml     # Docker Compose配置
├── 启动项目.bat          # Windows启动脚本
├── 启动说明.md           # 详细启动说明
└── README.md             # 本文档
```

## 🚀 快速开始

### 方式一：Docker Compose启动（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/ViVi141/mnr-law-crawler-online.git
cd MNR-Law-Crawler-Online

# 2. 启动所有服务
docker-compose up -d

# 3. 访问应用
# 前端：http://localhost:3000
# 后端API文档：http://localhost:8000/docs
```

### 方式二：本地开发启动

#### 后端启动

```bash
cd backend

# 1. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置数据库
# 编辑 backend/config.json 配置数据库连接信息

# 4. 初始化数据库
# 数据库迁移会自动执行

# 5. 启动后端服务
python -m app.main
# 或使用启动脚本
.\启动后端.ps1  # Windows
```

#### 前端启动

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 配置环境变量
# 创建 .env 文件，设置 VITE_API_BASE_URL=http://localhost:8000

# 3. 启动开发服务器
npm run dev
```

### 方式三：Windows一键启动

使用提供的批处理脚本：

```bash
启动项目.bat
```

脚本会自动启动前端和后端服务。

## ⚙️ 配置说明

### 数据库配置

在 `backend/config.json` 中配置数据库连接：

```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "mnr_crawler",
    "user": "your_username",
    "password": "your_password"
  }
}
```

### 爬虫配置

在系统设置的"爬虫配置"中可配置：
- **请求延迟**：默认0.5秒，可根据需要调整
- **代理设置**：目前不支持（目标网站无防护）

### 数据源配置

支持配置多个数据源，每个数据源可独立设置：
- `name`: 数据源名称
- `base_url`: 基础URL
- `search_api`: 搜索API
- `ajax_api`: AJAX API
- `channel_id`: 频道ID
- `enabled`: 是否启用

### S3存储配置（可选）

在系统设置的"S3存储配置"中配置：
- S3访问密钥
- S3存储桶名称
- S3区域

### 邮件服务配置（可选）

在系统设置的"邮件服务配置"中配置SMTP信息，用于任务完成通知。

## 📖 使用指南

### 创建爬取任务

1. 进入"任务管理"页面
2. 点击"创建任务"
3. 配置任务参数：
   - **任务名称**：给任务起个名字
   - **关键词**：可选，留空则全量爬取
   - **日期范围**：可选，指定爬取的时间范围
   - **数据源**：选择一个或多个数据源
   - **最大页数**：限制爬取的页数（可选）
   - **自动启动**：是否创建后立即启动
4. 点击"创建"按钮

### 搜索政策

1. 进入"政策列表"页面
2. 使用搜索表单筛选政策：
   - **关键词**：全文搜索
   - **分类**：按分类筛选
   - **数据源**：按数据源筛选
   - **日期范围**：按发布日期筛选
   - **发布机构**：按发布机构筛选
3. 点击"搜索"按钮

### 查看政策详情

1. 在政策列表中点击政策标题
2. 查看完整的政策信息
3. 下载政策文件（JSON/Markdown/DOCX）

### 创建定时任务

1. 进入"定时任务"页面
2. 点击"创建定时任务"
3. 配置Cron表达式和任务参数
4. 启用定时任务

## 🔧 开发说明

### 后端开发

```bash
cd backend
python -m app.main
```

后端API文档自动生成在：http://localhost:8000/docs

### 前端开发

```bash
cd frontend
npm run dev
```

前端开发服务器运行在：http://localhost:3000

### 代码检查

```bash
# 后端导入检查
cd backend
python check_imports.py  # 如果脚本存在

# 前端代码检查
cd frontend
npm run lint
```

## 📊 数据流架构

详细的系统数据流和架构说明请查看：
- [数据流导图.md](数据流导图.md) - 完整的数据流说明
- [数据流图表-Mermaid.md](数据流图表-Mermaid.md) - 可视化流程图

## 🗄️ 数据库

项目使用PostgreSQL数据库，主要表结构：

- **users** - 用户表
- **policies** - 政策表
- **tasks** - 任务表
- **attachments** - 附件表
- **scheduled_tasks** - 定时任务表
- **system_config** - 系统配置表
- **backup_records** - 备份记录表

数据库迁移使用Alembic管理，位于 `backend/migrations/` 目录。

## 🔐 安全说明

- 使用JWT Token进行身份认证
- 密码使用BCrypt加密存储
- API接口除登录外都需要认证
- 支持密码修改和重置功能

## 📄 许可证

本项目采用 **MIT License** 开源许可证。

## 👥 作者

**ViVi141**

- **GitHub**: [@ViVi141](https://github.com/ViVi141)
- **邮箱**: 747384120@qq.com

**项目名称**: MNR-Law-Crawler-Online  
**英文全称**: MNR Law Crawler Online  
**中文名称**: 自然资源部法规爬虫系统（Web版）  
**项目类型**: 全新Web应用项目  
**爬虫核心**: 基于原 [mnr-law-crawler](https://github.com/ViVi141/mnr-law-crawler) 项目的爬虫逻辑

---

**版本**: 1.1.0  
**最后更新**: 2025-12-08  
**项目主页**: https://github.com/ViVi141/mnr-law-crawler-online  
**原爬虫项目**: https://github.com/ViVi141/mnr-law-crawler

## 📝 更新日志

### v1.1.0 (2025-12-08) - BUG修复与系统优化

#### 🐛 严重BUG修复
- 🔧 **修复任务统计错误**：修复了`failed_count`计算错误，确保任务统计信息准确
  - 修复了所有政策（无论成功还是失败）都被计入`failed_count`的问题
  - 现在`failed_count`只在保存失败时正确增加
- 🔧 **修复S3文件路径不一致**：修复了任务完成后检查S3上传时路径不匹配的问题
  - 统一使用包含`task_id`的文件路径格式：`policies/{task_id}/{policy_id}/{policy_id}.md`
  - 确保文件保存和检查时使用相同的路径规则
- 🔧 **修复文件清理逻辑**：修复了文件清理时政策ID提取错误的问题
  - 使用记录的原始文件路径来匹配文件，而不是通过文件名提取ID
  - 解决了文件名中的`markdown_number`与`policy.id`不一致导致的清理失败问题
- 🔧 **修复附件路径问题**：修复了附件路径不包含`task_id`的问题
  - 附件路径现在包含`task_id`，确保不同任务的附件独立存储
  - 修复了`save_attachment`函数调用时缺少`task_id`参数的问题
- 🔧 **修复文件清理函数**：为`cleanup_policy_files`函数添加了`task_id`参数支持
  - 确保删除文件时使用正确的路径（包含`task_id`）
  - 避免文件残留和路径错误问题

#### 🎯 系统优化
- 📊 **数据独立性增强**：所有文件路径现在都包含`task_id`，确保不同任务的数据完全独立
- 🗂️ **文件管理改进**：改进了文件保存和清理逻辑，提高了文件管理的可靠性
- 🔍 **代码质量提升**：修复了多个数据流一致性问题，提高了系统的稳定性

#### 📝 数据库迁移
- ✨ **新增迁移**：`005_add_backup_source_fields.py` - 添加备份源字段
- ✨ **新增迁移**：`006_add_policy_task_id.py` - 为政策表添加`task_id`字段

#### 🛠️ 技术改进
- 📦 **新增工具模块**：`backend/app/services/utils.py` - 通用工具函数
- 🔄 **服务层优化**：优化了多个服务层的代码逻辑和错误处理
  - 优化了`task_service.py`中的文件保存和清理逻辑
  - 改进了`storage_service.py`中的文件路径管理
  - 增强了`policy_service.py`中的数据处理逻辑

#### 📋 修改文件列表
本次更新涉及以下主要文件：
- `backend/app/services/task_service.py` - 修复任务统计和文件清理逻辑
- `backend/app/services/storage_service.py` - 修复文件路径和附件管理
- `backend/app/models/policy.py` - 添加`task_id`字段支持
- `backend/migrations/versions/006_add_policy_task_id.py` - 数据库迁移
- 其他相关服务层和API层的优化

### v1.0.0 (2025-12-08) - 初始版本发布

#### 核心功能
- ✨ **Web化架构**：全新的前后端分离架构设计
- 🌐 **前端框架**：Vue 3 + TypeScript + Element Plus构建的现代化界面
- 🚀 **后端框架**：FastAPI构建的高性能RESTful API服务
- 📚 **政策库管理**：完整的政策存储、搜索、管理功能
- 🔍 **全文搜索**：基于PostgreSQL的全文搜索功能，支持多维度筛选
- 🎮 **任务管理**：可视化任务创建、监控和管理
- ⏰ **定时任务**：支持Cron表达式的定时爬取任务

#### 爬虫功能
- 🕷️ **爬虫核心**：集成原项目的成熟爬虫逻辑
- 🛡️ **多数据源**：支持多个数据源并行爬取（政府信息公开平台、政策法规库）
- 🔄 **智能解析**：针对不同数据源的专用HTML解析器
- ⏱️ **时间过滤**：支持日期范围筛选，实现增量爬取
- 🔍 **关键词搜索**：支持关键词筛选或全量爬取
- ⚡ **可配置延迟**：支持设置请求延迟，保护目标服务器

#### 存储与备份
- 💾 **多格式存储**：自动保存JSON、Markdown、DOCX和原始文件
- ☁️ **S3存储支持**：可选配置AWS S3或兼容的对象存储服务
- 💾 **数据库备份**：PostgreSQL数据库备份和恢复功能
- 🔄 **自动清理**：支持清理旧文件和备份

#### 系统功能
- 🔐 **用户认证**：JWT Token认证和用户管理
- ⚙️ **系统配置**：灵活的功能开关和系统配置管理
- 📊 **实时监控**：任务进度实时更新和统计信息
- 🔔 **邮件通知**：任务完成/失败邮件通知（可选）
- 📱 **响应式设计**：支持不同屏幕尺寸，良好的移动端体验

#### 技术特性
- 🎨 **现代化UI**：基于Element Plus的美观界面设计
- 📦 **容器化部署**：支持Docker Compose一键部署
- 🔧 **数据库迁移**：使用Alembic管理数据库版本
- 📊 **数据流可视化**：完整的数据流和架构文档

## 🔗 相关项目

### 原爬虫项目
本项目使用的爬虫核心逻辑来自：

**[mnr-law-crawler](https://github.com/ViVi141/mnr-law-crawler)** - 原GUI/CLI版本的爬虫工具
- 提供了成熟的爬虫核心逻辑
- 包含多数据源支持和HTML解析器
- 包含智能内容清洗和元信息提取功能
- 本项目在此基础上构建了完整的Web管理系统

### 项目关系

- **mnr-law-crawler**: 原项目，提供爬虫核心逻辑（GUI/CLI工具）
- **mnr-law-crawler-online**: 本项目，基于原爬虫逻辑构建的Web应用系统（全新项目）

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至：747384120@qq.com

---

**感谢使用 MNR Law Crawler！** 🎉
