<template>
  <div class="backups-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>备份管理</h2>
          <div>
            <el-button type="primary" @click="showCreateDialog = true">
              <el-icon><Plus /></el-icon>
              创建备份
            </el-button>
            <el-button @click="handleCleanup">
              <el-icon><Delete /></el-icon>
              清理旧备份
            </el-button>
          </div>
        </div>
      </template>

      <!-- 备份列表 -->
      <el-table v-loading="loading" :data="backups" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="backup_type" label="备份类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.backup_type === 'full' ? 'primary' : 'success'">
              {{ row.backup_type === 'full' ? '完整备份' : '增量备份' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ row.completed_at ? formatDateTime(row.completed_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="file_path" label="文件路径" min-width="300" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'completed'"
              link
              type="primary"
              @click="handleRestore(row)"
            >
              恢复
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </el-card>

    <!-- 创建备份对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建备份" width="500px">
      <el-form :model="backupForm" label-width="100px">
        <el-form-item label="备份类型">
          <el-select v-model="backupForm.backup_type" placeholder="请选择备份类型">
            <el-option label="完整备份" value="full" />
            <el-option label="增量备份" value="incremental" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateBackup">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { backupsApi } from '../api/backups'
import type { BackupRecord } from '../types/backup'
import type { ApiError } from '../types/common'
import dayjs from 'dayjs'

const loading = ref(false)
const creating = ref(false)
const backups = ref<BackupRecord[]>([])
const showCreateDialog = ref(false)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const backupForm = reactive({
  backup_type: 'full',
})

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待处理',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
  }
  return statusMap[status] || status
}

const fetchBackups = async () => {
  loading.value = true
  try {
    const response = await backupsApi.getBackups({
      page: pagination.page,
      page_size: pagination.pageSize,
    })
    backups.value = response.items || response.backups || []
    pagination.total = response.total || 0
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '获取备份列表失败')
  } finally {
    loading.value = false
  }
}

const handleSizeChange = () => {
  pagination.page = 1
  fetchBackups()
}

const handlePageChange = () => {
  fetchBackups()
}

const handleCreateBackup = async () => {
  creating.value = true
  try {
    await backupsApi.createBackup({ backup_type: backupForm.backup_type })
    ElMessage.success('备份任务已创建')
    showCreateDialog.value = false
    backupForm.backup_type = 'full'
    await fetchBackups()
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '创建备份失败')
  } finally {
    creating.value = false
  }
}

const handleRestore = async (backup: BackupRecord) => {
  try {
    await ElMessageBox.confirm(
      `确定要恢复备份 ${backup.id} 吗？此操作将覆盖当前数据库！`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await backupsApi.restoreBackup(backup.id, { confirm: true })
    ElMessage.success('备份恢复任务已启动')
    await fetchBackups()
  } catch (error) {
    // ElMessageBox.confirm 取消时会抛出 'cancel' 字符串
    if (typeof error === 'string' && error === 'cancel') {
      return
    }
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '恢复备份失败')
  }
}

const handleDelete = async (backup: BackupRecord) => {
  try {
    await ElMessageBox.confirm('确定要删除这个备份吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await backupsApi.deleteBackup(backup.id)
    ElMessage.success('备份已删除')
    await fetchBackups()
  } catch (error) {
    // ElMessageBox.confirm 取消时会抛出 'cancel' 字符串
    if (typeof error === 'string' && error === 'cancel') {
      return
    }
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '删除备份失败')
  }
}

const handleCleanup = async () => {
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入要保留的备份数量',
      '清理旧备份',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /^\d+$/,
        inputErrorMessage: '请输入有效的数字',
      }
    )

    const keepCount = parseInt(value)
    const result = await backupsApi.cleanupBackups({ keep_count: keepCount })
    ElMessage.success(`已清理 ${result.deleted_count} 个旧备份`)
    await fetchBackups()
  } catch (error) {
    // ElMessageBox.prompt 取消时会抛出 'cancel' 字符串
    if (typeof error === 'string' && error === 'cancel') {
      return
    }
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '清理备份失败')
  }
}

onMounted(() => {
  fetchBackups()
})
</script>

<style lang="scss" scoped>
.backups-page {
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

    h2 {
      margin: 0;
      font-size: 20px;
    }
    
    > div {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
  }
  
  // 响应式表格
  :deep(.el-table) {
    .el-table__body-wrapper {
      overflow-x: auto;
    }
  }
  
  // 对话框内容滚动
  :deep(.el-dialog__body) {
    max-height: 70vh;
    overflow-y: auto;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .backups-page {
    .card-header {
      h2 {
        font-size: 18px;
      }
    }
  }
}
</style>

