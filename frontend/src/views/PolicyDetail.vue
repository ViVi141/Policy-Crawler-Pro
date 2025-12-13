<template>
  <div class="policy-detail-page">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <el-button @click="router.back()">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <div class="header-actions">
            <el-button
              v-if="policy?.sourceUrl"
              type="primary"
              @click="handleViewSource"
            >
              原文链接 <el-icon><Link /></el-icon>
            </el-button>
            <el-dropdown @command="handleDownload">
              <el-button type="primary">
                下载 <el-icon><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="markdown">Markdown</el-dropdown-item>
                  <el-dropdown-item command="docx">DOCX</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <div v-if="policy" class="policy-content">
        <!-- 标题区域 -->
        <div class="policy-header">
          <h1 class="policy-title">{{ policy.title }}</h1>
          <div class="policy-badges">
            <el-tag v-if="policy.validity" type="info" size="large">{{ policy.validity }}</el-tag>
            <el-tag v-if="policy.lawLevel" :type="getLawLevelType(policy.lawLevel)" size="large">
              {{ policy.lawLevel }}
            </el-tag>
          </div>
        </div>

        <!-- 基本信息卡片 -->
        <el-card class="info-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><InfoFilled /></el-icon>
              <span>基本信息</span>
            </div>
          </template>

          <el-descriptions :column="{ xs: 1, sm: 2, md: 2, lg: 3, xl: 3 }" border class="policy-meta">
            <el-descriptions-item label="数据来源">
              <el-tag type="success">{{ policy.sourceName || policy.source_name || '未知' }}</el-tag>
            </el-descriptions-item>

            <el-descriptions-item label="分类">
              {{ policy.category === '全部' ? '全部分类' : policy.category || '未分类' }}
            </el-descriptions-item>

            <el-descriptions-item label="发布机构" :span="2">
              <span v-if="policy.publisher" class="highlight-text">{{ policy.publisher }}</span>
              <span v-else-if="policy.lawLevel" class="highlight-text">{{ policy.lawLevel }}</span>
              <span v-else class="empty-text">-</span>
            </el-descriptions-item>

            <el-descriptions-item label="发布日期">
              <span class="date-text">{{ formatDate(policy.publishDate || '') }}</span>
            </el-descriptions-item>

            <el-descriptions-item label="生效日期">
              <span class="date-text">{{ formatDate(policy.effectiveDate || '') || '未指定' }}</span>
            </el-descriptions-item>

            <el-descriptions-item label="文号" :span="3">
              <span v-if="policy.docNumber" class="doc-number">{{ policy.docNumber }}</span>
              <span v-else class="empty-text">-</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 系统信息卡片 -->
        <el-card class="system-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Clock /></el-icon>
              <span>系统信息</span>
            </div>
          </template>

          <el-descriptions :column="2" border class="system-meta">
            <el-descriptions-item label="创建时间">
              <span class="datetime-text">{{ formatDateTime(policy.createdAt || '') }}</span>
            </el-descriptions-item>

            <el-descriptions-item label="最后更新">
              <span class="datetime-text">{{ formatDateTime(policy.updatedAt || '') }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <div v-if="policy.keywords && policy.keywords.length > 0" class="keywords-section">
          <el-tag
            v-for="keyword in policy.keywords"
            :key="keyword"
            style="margin-right: 8px; margin-bottom: 8px"
          >
            {{ keyword }}
          </el-tag>
        </div>

        <div v-if="policy.summary" class="summary-section">
          <h3>摘要</h3>
          <p>{{ policy.summary }}</p>
        </div>

        <div v-if="policy.content" class="content-section">
          <h3>内容</h3>
          <div class="content-body" v-html="formatContent(policy.content)"></div>
        </div>

        <div v-if="policy.attachments && policy.attachments.length > 0" class="attachments-section">
          <h3>附件</h3>
          <el-table :data="policy.attachments" stripe>
            <el-table-column prop="filename" label="文件名" />
            <el-table-column prop="file_type" label="类型" width="100" />
            <el-table-column label="大小" width="120">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button link type="primary" @click="downloadAttachment(row)">
                  下载
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowDown, Link, InfoFilled, Clock } from '@element-plus/icons-vue'
import { policiesApi } from '../api/policies'
import type { Policy } from '../types/policy'
import type { ApiError } from '../types/common'
import type { Attachment } from '../types/common'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const policy = ref<Policy | null>(null)

const formatDate = (date: string) => {
  if (!date || date === '') {
    return '-'
  }
  const parsed = dayjs(date)
  if (!parsed.isValid()) {
    return 'Invalid Date'
  }
  return parsed.format('YYYY-MM-DD')
}

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const formatContent = (content: string) => {
  // HTML内容格式化：处理换行和空格，避免奇怪换行
  if (!content) return ''
  
  // 先转义HTML特殊字符
  let formatted = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
  
  // 修复被错误拆分的数字和括号（如 \n2022\n）
  formatted = formatted.replace(/\n+(\d{4})\s*\n+/g, '$1')
  formatted = formatted.replace(/\n+(\d+[号条款项])/g, '$1')
  
  // 将换行符转换为<br/>，但多个连续换行只保留一个
  formatted = formatted.replace(/\n{3,}/g, '\n\n')
  formatted = formatted.replace(/\n/g, '<br/>')
  
  // 合并多个连续的<br/>标签（最多保留两个）
  formatted = formatted.replace(/(<br\/>){3,}/g, '<br/><br/>')
  
  return formatted
}

const fetchPolicy = async () => {
  const id = parseInt(route.params.id as string)
  if (!id) {
    ElMessage.error('无效的政策ID')
    router.push('/policies')
    return
  }

  loading.value = true
  try {
    policy.value = await policiesApi.getPolicyById(id)
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '获取政策详情失败')
    router.push('/policies')
  } finally {
    loading.value = false
  }
}

const handleViewSource = () => {
  if (policy.value?.sourceUrl) {
    window.open(policy.value.sourceUrl, '_blank')
  }
}

const getLawLevelType = (lawLevel: string) => {
  if (lawLevel.includes('自然资源部')) return 'success'
  if (lawLevel.includes('国务院')) return 'warning'
  if (lawLevel.includes('部')) return 'info'
  return 'primary'
}

const handleDownload = async (fileType: string) => {
  if (!policy.value) return

  try {
    const blob = await policiesApi.downloadPolicy(policy.value.id, fileType)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // 将文件类型转换为实际扩展名（markdown -> md）
    const fileExt = fileType === 'markdown' ? 'md' : fileType
    a.download = `${policy.value.title}.${fileExt}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载开始')
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '下载失败')
  }
}

const downloadAttachment = async (attachment: Attachment) => {
  if (!policy.value) return

  try {
    const blob = await policiesApi.downloadAttachment(policy.value.id, attachment.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = attachment.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载开始')
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '下载附件失败')
  }
}

onMounted(() => {
  fetchPolicy()
})
</script>

<style lang="scss" scoped>
.policy-detail-page {
  width: 100%;
  min-height: 100%;
  
  :deep(.el-card) {
    height: 100%;
    display: flex;
    flex-direction: column;
    
    .el-card__body {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    
    .header-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
  }

  .policy-content {
    width: 100%;
    
    .policy-title {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 20px;
      color: #303133;
      word-wrap: break-word;
      line-height: 1.5;
    }

    .policy-meta {
      margin-bottom: 20px;
      
      :deep(.el-descriptions) {
        .el-descriptions__label {
          font-weight: 500;
        }
      }
    }

    .keywords-section {
      margin-bottom: 20px;
      padding: 15px;
      background-color: #f5f7fa;
      border-radius: 4px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .summary-section,
    .content-section,
    .attachments-section {
      margin-top: 30px;

      h3 {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 15px;
        color: #303133;
      }

      p {
        line-height: 1.8;
        color: #606266;
        word-wrap: break-word;
      }
    }

    .content-body {
      line-height: 1.8;
      color: #606266;
      padding: 20px;
      background-color: #fafafa;
      border-radius: 4px;
      white-space: pre-wrap;
      word-wrap: break-word;
      overflow-x: auto;
      max-width: 100%;
    }
    
    // 附件表格
    :deep(.attachments-section) {
      .el-table {
        .el-table__body-wrapper {
          overflow-x: auto;
        }
      }
    }

    // 新的布局样式
    .policy-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
      gap: 16px;

      .policy-title {
        flex: 1;
        font-size: 24px;
        font-weight: 600;
        color: #303133;
        line-height: 1.4;
        margin: 0;
      }

      .policy-badges {
        display: flex;
        gap: 8px;
        flex-shrink: 0;
        flex-wrap: wrap;
      }
    }

    .info-card,
    .system-card {
      margin-bottom: 24px;

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

    .policy-meta,
    .system-meta {
      :deep(.el-descriptions__title) {
        font-weight: 600;
        color: #606266;
        min-width: 100px;
      }

      :deep(.el-descriptions__content) {
        color: #303133;
      }
    }

    .highlight-text {
      font-weight: 600;
      color: #303133;
    }

    .doc-number {
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 14px;
      background: #f8f9fa;
      padding: 4px 8px;
      border-radius: 4px;
      color: #e74c3c;
    }

    .date-text,
    .datetime-text {
      color: #606266;
      font-size: 14px;
    }

    .empty-text {
      color: #c0c4cc;
      font-style: italic;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .policy-detail-page {
    .policy-content {
      .policy-title {
        font-size: 20px;
      }
      
      .policy-meta {
        :deep(.el-descriptions) {
          .el-descriptions__table {
            .el-descriptions__label,
            .el-descriptions__content {
              display: block;
              width: 100%;
              padding: 8px 0;
            }
          }
        }
      }
      
      .content-body {
        padding: 15px;
        font-size: 14px;
      }
    }
  }
}
</style>

