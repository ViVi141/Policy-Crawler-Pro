<!--
==============================================================================
MNR Law Crawler Online - 关于页面
==============================================================================

项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
作者: ViVi141
许可证: MIT License

描述: 关于页面的Vue组件，展示项目信息、技术栈和功能特性

==============================================================================
-->
<template>
  <div class="about-page">
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="project-title">MNR Law Crawler Online</h1>
        <p class="project-subtitle">自然资源部法规爬虫系统 - Web版</p>
        <div class="version-badge">
          <el-tag type="success" size="large">v3.0.0</el-tag>
        </div>
      </div>
      <div class="hero-image">
        <el-icon size="80" class="hero-icon"><DataAnalysis /></el-icon>
      </div>
    </div>

    <div class="content-section">
      <!-- 项目简介 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><InfoFilled /></el-icon>
            <span>项目简介</span>
          </div>
        </template>
        <div class="project-description">
          <p>
            这是一个全新的Web应用项目，用于管理和爬取自然资源部政策法规数据。
            项目采用了现代化的前后端分离架构，提供了完整的政策法规库管理功能。
          </p>
          <p>
            系统集爬取、存储、搜索、管理于一体的现代化政策法规库系统，
            支持多数据源并行爬取、智能内容解析、实时任务监控等企业级功能。
          </p>
        </div>
      </el-card>

      <!-- 项目声明 -->
      <el-card class="info-card project-notice" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Warning /></el-icon>
            <span>项目声明</span>
          </div>
        </template>
        <div class="project-notice-content">
          <div class="notice-section">
            <h4 class="notice-title">
              <el-icon class="notice-icon academic"><Reading /></el-icon>
              项目性质
            </h4>
            <p class="notice-text">
              <strong>本项目主要为学术研究提供基础数据支持</strong>，并非我的主要项目。
              虽然我已经投入了大量精力构建完整的CI/CD流程，但由于项目定位和个人精力有限，
              <strong>无法保证及时的更新和BUG修复</strong>。
            </p>
          </div>

          <div class="notice-section">
            <h4 class="notice-title">
              <el-icon class="notice-icon maintenance"><Clock /></el-icon>
              维护状态
            </h4>
            <ul class="notice-list">
              <li><strong>更新频率：</strong>不定期更新，主要在有学术需求时进行改进</li>
              <li><strong>BUG修复：</strong>优先处理严重影响学术研究的BUG，其他问题可能延迟处理</li>
              <li><strong>功能扩展：</strong>主要围绕学术研究需求进行功能优化</li>
              <li><strong>技术支持：</strong>社区驱动，欢迎提交PR贡献代码</li>
            </ul>
          </div>

          <div class="notice-section">
            <h4 class="notice-title">
              <el-icon class="notice-icon usage"><Star /></el-icon>
              建议使用方式
            </h4>
            <ul class="notice-list">
              <li><strong>学术研究：</strong>推荐用于学术研究和数据收集</li>
              <li><strong>生产环境：</strong>建议谨慎评估，考虑商业技术支持服务</li>
              <li><strong>学习参考：</strong>适合学习现代Web应用架构和技术栈</li>
            </ul>
          </div>

          <div class="notice-section">
            <h4 class="notice-title">
              <el-icon class="notice-icon contribute"><User /></el-icon>
              贡献与反馈
            </h4>
            <p class="notice-text">
              欢迎所有开发者贡献代码和建议！虽然维护响应可能不及时，
              但每个贡献都会被认真考虑和感谢。
            </p>
          </div>
        </div>
      </el-card>

      <!-- 核心特性 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Star /></el-icon>
            <span>核心特性</span>
          </div>
        </template>
        <div class="features-grid">
          <div class="feature-item">
            <el-icon class="feature-icon"><Monitor /></el-icon>
            <div class="feature-content">
              <h4>现代化Web界面</h4>
              <p>Vue 3 + TypeScript + Element Plus构建的美观Web界面，支持响应式设计</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><Connection /></el-icon>
            <div class="feature-content">
              <h4>RESTful API</h4>
              <p>FastAPI构建的高性能后端服务，支持异步处理和自动文档生成</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><Aim /></el-icon>
            <div class="feature-content">
              <h4>智能爬虫</h4>
              <p>支持多数据源并行爬取，智能HTML解析，关键词筛选，时间范围过滤</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><Search /></el-icon>
            <div class="feature-content">
              <h4>全文搜索</h4>
              <p>基于PostgreSQL的全文搜索功能，支持多维度筛选和关键词高亮</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><Clock /></el-icon>
            <div class="feature-content">
              <h4>定时任务</h4>
              <p>支持Cron表达式配置定时爬取任务，灵活的调度管理</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><Box /></el-icon>
            <div class="feature-content">
              <h4>备份恢复</h4>
              <p>完整的数据库和文件备份恢复功能，支持多种存储策略</p>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 技术架构 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Setting /></el-icon>
            <span>技术架构</span>
          </div>
        </template>
        <div class="tech-stack">
          <div class="tech-section">
            <h3>前端技术栈</h3>
            <div class="tech-items">
              <el-tag type="primary">Vue 3</el-tag>
              <el-tag type="primary">TypeScript</el-tag>
              <el-tag type="primary">Element Plus</el-tag>
              <el-tag type="primary">Pinia</el-tag>
              <el-tag type="primary">Vue Router</el-tag>
              <el-tag type="primary">Axios</el-tag>
              <el-tag type="primary">Vite</el-tag>
            </div>
          </div>
          <div class="tech-section">
            <h3>后端技术栈</h3>
            <div class="tech-items">
              <el-tag type="success">FastAPI</el-tag>
              <el-tag type="success">Python 3.11+</el-tag>
              <el-tag type="success">SQLAlchemy</el-tag>
              <el-tag type="success">PostgreSQL</el-tag>
              <el-tag type="success">APScheduler</el-tag>
              <el-tag type="success">JWT</el-tag>
            </div>
          </div>
          <div class="tech-section">
            <h3>部署方案</h3>
            <div class="tech-items">
              <el-tag type="warning">Docker</el-tag>
              <el-tag type="warning">Docker Compose</el-tag>
              <el-tag type="warning">Nginx</el-tag>
              <el-tag type="warning">PostgreSQL</el-tag>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 项目信息 -->
      <div class="info-grid">
        <el-card class="info-card small-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><User /></el-icon>
              <span>作者信息</span>
            </div>
          </template>
          <div class="author-info">
            <p><strong>作者：</strong>ViVi141</p>
            <p><strong>邮箱：</strong>747384120@qq.com</p>
            <p><strong>GitHub：</strong>
              <el-link href="https://github.com/ViVi141" target="_blank" type="primary">
                @ViVi141
              </el-link>
            </p>
          </div>
        </el-card>

        <el-card class="info-card small-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>项目信息</span>
            </div>
          </template>
          <div class="project-info">
            <p><strong>项目名称：</strong>MNR Law Crawler Online</p>
            <p><strong>版本：</strong>v3.0.0</p>
            <p><strong>许可证：</strong>MIT License</p>
            <p><strong>发布日期：</strong>2025-12-13</p>
          </div>
        </el-card>

        <el-card class="info-card small-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Link /></el-icon>
              <span>相关链接</span>
            </div>
          </template>
          <div class="links-info">
            <p>
              <el-link href="https://github.com/ViVi141/MNR-Law-Crawler-Online" target="_blank" type="primary">
                <el-icon><Link /></el-icon>
                项目主页
              </el-link>
            </p>
            <p>
              <el-link href="https://github.com/ViVi141/MNR-Law-Crawler-Online/blob/main/README.md" target="_blank" type="primary">
                <el-icon><Document /></el-icon>
                项目文档
              </el-link>
            </p>
            <p>
              <el-link href="https://github.com/ViVi141/MNR-Law-Crawler-Online/issues" target="_blank" type="primary">
                <el-icon><Warning /></el-icon>
                问题反馈
              </el-link>
            </p>
          </div>
        </el-card>
      </div>

      <!-- 使用条款 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>使用条款</span>
          </div>
        </template>
        <div class="usage-terms">
          <div class="term-section">
            <h4 class="term-title">
              <el-icon class="term-icon success"><Check /></el-icon>
              商业使用许可
            </h4>
            <ul class="term-list">
              <li>允许通过购买、租借、订阅等方式合法使用本项目</li>
              <li>在获得授权后，您可以分发本项目的副本</li>
              <li>可选择购买技术支持服务</li>
            </ul>
          </div>

          <div class="term-section">
            <h4 class="term-title">
              <el-icon class="term-icon star"><Star /></el-icon>
              项目支持
            </h4>
            <div class="star-section">
              <p class="star-text">
                <strong>如果您喜欢这个项目，请到GitHub原项目点个STAR！</strong>
              </p>
              <el-link
                href="https://github.com/ViVi141/MNR-Law-Crawler-Online"
                target="_blank"
                type="primary"
                class="github-link"
              >
                <el-icon><Link /></el-icon>
                GitHub项目主页
                <el-icon class="external-icon"><TopRight /></el-icon>
              </el-link>
            </div>
          </div>

          <div class="term-section warning">
            <h4 class="term-title">
              <el-icon class="term-icon warning"><Warning /></el-icon>
              重要声明
            </h4>
            <div class="warning-content">
              <p class="warning-text">
                <strong>严禁用于非法用途！</strong>
              </p>
              <ul class="warning-list">
                <li>所有开发者与用户必须遵守当地法律法规</li>
                <li>不得将本项目用于任何违法违规活动</li>
                <li>不得侵犯他人知识产权和隐私权</li>
                <li>使用者对使用本项目产生的后果负全部责任</li>
              </ul>
            </div>
          </div>

          <div class="term-section">
            <h4 class="term-title">
              <el-icon class="term-icon info"><InfoFilled /></el-icon>
              免责声明
            </h4>
            <p class="disclaimer-text">
              本项目按"现状"提供，不提供任何明示或暗示的保证。
              作者不对使用本项目产生的任何直接或间接损害承担责任。
            </p>
          </div>
        </div>
      </el-card>

      <!-- 许可证信息 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><DocumentChecked /></el-icon>
            <span>许可证信息</span>
          </div>
        </template>
        <div class="license-content">
          <div class="license-header">
            <h3>MIT License</h3>
            <p>Copyright (c) 2025 ViVi141</p>
          </div>
          <div class="license-text">
            <p>
              Permission is hereby granted, free of charge, to any person obtaining a copy
              of this software and associated documentation files (the "Software"), to deal
              in the Software without restriction, including without limitation the rights
              to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
              copies of the Software, and to permit persons to whom the Software is
              furnished to do so, subject to the following conditions:
            </p>
            <p>
              The above copyright notice and this permission notice shall be included in all
              copies or substantial portions of the Software.
            </p>
            <p class="license-note">
              THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
              IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
              FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
              AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
              LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
              OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
              SOFTWARE.
            </p>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  InfoFilled,
  Star,
  Monitor,
  Connection,
  Aim,
  Search,
  Clock,
  Box,
  Setting,
  User,
  Document,
  Link,
  Warning,
  DocumentChecked,
  DataAnalysis,
  Check,
  TopRight,
  Reading,
} from '@element-plus/icons-vue'
</script>

<style lang="scss" scoped>
.about-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 60px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  margin-bottom: 30px;
  color: white;

  .hero-content {
    flex: 1;

    .project-title {
      font-size: 3rem;
      font-weight: 700;
      margin: 0 0 10px 0;
      background: linear-gradient(45deg, #fff, #e0e7ff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .project-subtitle {
      font-size: 1.2rem;
      margin: 0 0 20px 0;
      opacity: 0.9;
    }

    .version-badge {
      display: inline-block;
    }
  }

  .hero-image {
    flex-shrink: 0;
    margin-left: 40px;
    opacity: 0.8;

    .hero-icon {
      filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
    }
  }
}

.content-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card {
  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: #303133;

    .el-icon {
      color: #409eff;
    }
  }
}

.project-notice {
  border-left: 4px solid #e6a23c;
  background: linear-gradient(135deg, #fff7e6 0%, #fff9f0 100%);

  .card-header {
    .el-icon {
      color: #e6a23c;
    }
  }
}

.project-notice-content {
  .notice-section {
    margin-bottom: 20px;

    &:last-child {
      margin-bottom: 0;
    }

    .notice-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 8px 0;
      color: #303133;
      font-size: 14px;
      font-weight: 600;

      .notice-icon {
        &.academic {
          color: #67c23a;
        }

        &.maintenance {
          color: #409eff;
        }

        &.usage {
          color: #e6a23c;
        }

        &.contribute {
          color: #909399;
        }
      }
    }

    .notice-text {
      margin: 0;
      color: #606266;
      line-height: 1.6;
      font-size: 13px;
    }

    .notice-list {
      margin: 0;
      padding-left: 16px;
      color: #606266;
      line-height: 1.6;
      font-size: 13px;

      li {
        margin-bottom: 4px;

        &:last-child {
          margin-bottom: 0;
        }

        strong {
          color: #303133;
        }
      }
    }
  }
}

.project-description {
  p {
    margin: 0 0 16px 0;
    line-height: 1.6;
    color: #606266;
    font-size: 15px;

    &:last-child {
      margin-bottom: 0;
    }
  }
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;

  .feature-item {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 8px;
    transition: transform 0.2s, box-shadow 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .feature-icon {
      color: #409eff;
      flex-shrink: 0;
      margin-top: 2px;
    }

    .feature-content {
      h4 {
        margin: 0 0 8px 0;
        color: #303133;
        font-size: 16px;
        font-weight: 600;
      }

      p {
        margin: 0;
        color: #606266;
        line-height: 1.5;
        font-size: 14px;
      }
    }
  }
}

.tech-stack {
  .tech-section {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }

    h3 {
      margin: 0 0 12px 0;
      color: #303133;
      font-size: 16px;
      font-weight: 600;
    }

    .tech-items {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;

      .el-tag {
        margin: 0;
      }
    }
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 20px;

  .small-card {
    .author-info,
    .project-info,
    .links-info {
      p {
        margin: 0 0 8px 0;
        color: #606266;
        line-height: 1.5;

        &:last-child {
          margin-bottom: 0;
        }

        strong {
          color: #303133;
          font-weight: 600;
        }
      }
    }

    .links-info {
      .el-link {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 8px;

        &:last-child {
          margin-bottom: 0;
        }
      }
    }
  }
}

.usage-terms {
  .term-section {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }

    &.warning {
      background: #fff7e6;
      padding: 16px;
      border-radius: 8px;
      border-left: 4px solid #e6a23c;
    }

    .term-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 12px 0;
      color: #303133;
      font-size: 16px;
      font-weight: 600;

      .term-icon {
        &.success {
          color: #67c23a;
        }

        &.star {
          color: #e6a23c;
        }

        &.warning {
          color: #e6a23c;
        }

        &.info {
          color: #909399;
        }
      }
    }

    .term-list {
      margin: 0;
      padding-left: 20px;
      color: #606266;
      line-height: 1.6;

      li {
        margin-bottom: 4px;

        &:last-child {
          margin-bottom: 0;
        }
      }
    }

    .star-section {
      .star-text {
        margin: 0 0 12px 0;
        color: #e6a23c;
        font-size: 15px;
        line-height: 1.5;
      }

      .github-link {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-weight: 500;

        .external-icon {
          margin-left: 4px;
        }
      }
    }

    .warning-content {
      .warning-text {
        margin: 0 0 12px 0;
        color: #e6a23c;
        font-size: 15px;
        font-weight: 600;
        line-height: 1.5;
      }

      .warning-list {
        margin: 0;
        padding-left: 20px;
        color: #606266;
        line-height: 1.6;

        li {
          margin-bottom: 4px;
          color: #e6a23c;

          &:last-child {
            margin-bottom: 0;
          }
        }
      }
    }

    .disclaimer-text {
      margin: 0;
      color: #909399;
      line-height: 1.6;
      font-size: 14px;
      font-style: italic;
    }
  }
}

.license-content {
  .license-header {
    margin-bottom: 16px;

    h3 {
      margin: 0 0 4px 0;
      color: #303133;
      font-size: 18px;
    }

    p {
      margin: 0;
      color: #909399;
      font-size: 14px;
    }
  }

  .license-text {
    p {
      margin: 0 0 12px 0;
      line-height: 1.6;
      color: #606266;
      text-align: justify;

      &:last-child {
        margin-bottom: 0;
      }

      &.license-note {
        font-style: italic;
        color: #f56c6c;
        background: #fef0f0;
        padding: 12px;
        border-radius: 4px;
        border-left: 4px solid #f56c6c;
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
    padding: 40px 20px;

    .hero-content {
      .project-title {
        font-size: 2rem;
      }

      .project-subtitle {
        font-size: 1rem;
      }
    }

    .hero-image {
      margin-left: 0;
      margin-top: 20px;
    }
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .about-page {
    padding: 0 10px;
  }
}
</style>
