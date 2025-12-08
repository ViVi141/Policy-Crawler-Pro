<template>
  <div class="scheduled-tasks-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>定时任务管理</h2>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            新建定时任务
          </el-button>
        </div>
      </template>

      <!-- 任务列表 -->
      <el-table v-loading="loading" :data="scheduledTasks" stripe style="width: 100%">
        <el-table-column prop="task_name" label="任务名称" min-width="200" />
        <el-table-column prop="task_type" label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.task_type === 'crawl_task' ? 'primary' : 'success'">
              {{ row.task_type === 'crawl_task' ? '爬取任务' : '备份任务' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cron_expression" label="Cron表达式" width="150" />
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              :loading="row._toggling"
              @change="handleToggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="next_run_time" label="下次运行时间" width="180">
          <template #default="{ row }">
            {{ row.next_run_time ? formatDateTime(row.next_run_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="last_run_time" label="上次运行时间" width="180">
          <template #default="{ row }">
            {{ row.last_run_time ? formatDateTime(row.last_run_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="last_run_status" label="上次运行状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.last_run_status" :type="getStatusType(row.last_run_status)">
              {{ getStatusText(row.last_run_status) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
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

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTask ? '编辑定时任务' : '新建定时任务'"
      width="700px"
    >
      <el-form :model="taskForm" :rules="taskRules" ref="taskFormRef" label-width="120px">
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="taskForm.task_type" placeholder="请选择任务类型">
            <el-option label="爬取任务" value="crawl_task" />
            <el-option label="备份任务" value="backup_task" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="taskForm.task_name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="Cron表达式" prop="cron_expression">
          <el-input v-model="taskForm.cron_expression" placeholder="例如: 0 2 * * * (每天凌晨2点)">
            <template #append>
              <el-button @click="showCronHelp = true">帮助</el-button>
            </template>
          </el-input>
          <div class="cron-help-text">
            <p v-if="taskForm.cron_expression" class="cron-preview">
              预览: {{ parseCronExpression(taskForm.cron_expression) }}
            </p>
          </div>
        </el-form-item>
        <el-form-item v-if="taskForm.task_type === 'crawl_task'" label="关键词">
          <el-input
            v-model="taskForm.keywords"
            type="textarea"
            :rows="3"
            placeholder="多个关键词用逗号分隔，留空表示爬取全部"
          />
        </el-form-item>
        <el-form-item v-if="taskForm.task_type === 'backup_task'" label="备份类型">
          <el-select v-model="taskForm.backup_type" placeholder="请选择备份类型">
            <el-option label="完整备份" value="full" />
            <el-option label="增量备份" value="incremental" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="taskForm.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleCancelDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- Cron表达式帮助对话框 -->
    <el-dialog v-model="showCronHelp" title="Cron表达式帮助" width="600px">
      <div class="cron-help">
        <p><strong>格式:</strong> 分钟 小时 日 月 星期</p>
        <h4>示例:</h4>
        <ul>
          <li><code>0 2 * * *</code> - 每天凌晨2点</li>
          <li><code>0 9 * * *</code> - 每天上午9点</li>
          <li><code>0 2 * * 1</code> - 每周一凌晨2点</li>
          <li><code>0 2 1 * *</code> - 每月1号凌晨2点</li>
          <li><code>0 */6 * * *</code> - 每6小时</li>
          <li><code>*/30 * * * *</code> - 每30分钟</li>
          <li><code>0 9 * * 1-5</code> - 工作日上午9点</li>
        </ul>
        <h4>字段说明:</h4>
        <ul>
          <li><strong>分钟:</strong> 0-59</li>
          <li><strong>小时:</strong> 0-23</li>
          <li><strong>日:</strong> 1-31</li>
          <li><strong>月:</strong> 1-12</li>
          <li><strong>星期:</strong> 0-7 (0和7都表示周日)</li>
        </ul>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { scheduledTasksApi } from '../api/scheduledTasks'
import type {
  ScheduledTask,
  ScheduledTaskCreateRequest,
  ScheduledTaskListItem,
} from '../types/scheduledTask'
import type { ApiError, CrawlTaskConfig, BackupTaskConfig } from '../types/common'
import type { FormInstance, FormRules } from 'element-plus'
import dayjs from 'dayjs'

const loading = ref(false)
const saving = ref(false)
const scheduledTasks = ref<ScheduledTask[]>([])
const showCreateDialog = ref(false)
const showCronHelp = ref(false)
const editingTask = ref<ScheduledTask | null>(null)
const taskFormRef = ref<FormInstance>()

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const taskForm = reactive<{
  task_type: string
  task_name: string
  cron_expression: string
  keywords: string
  backup_type: string
  is_enabled: boolean
}>({
  task_type: 'crawl_task',
  task_name: '',
  cron_expression: '0 2 * * *',
  keywords: '',
  backup_type: 'full',
  is_enabled: true,
})

const taskRules: FormRules = {
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  cron_expression: [
    { required: true, message: '请输入Cron表达式', trigger: 'blur' },
    {
      pattern: /^(\*|([0-9]|[1-5][0-9])|\*\/([0-9]|[1-5][0-9])) (\*|([0-9]|1[0-9]|2[0-3])|\*\/([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|[12][0-9]|3[01])|\*\/([1-9]|[12][0-9]|3[01])) (\*|([1-9]|1[0-2])|\*\/([1-9]|1[0-2])) (\*|([0-7])|\*\/([0-7]))$/,
      message: 'Cron表达式格式不正确',
      trigger: 'blur',
    },
  ],
}

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    success: 'success',
    failed: 'danger',
    running: 'warning',
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    success: '成功',
    failed: '失败',
    running: '运行中',
  }
  return statusMap[status] || status
}

const parseCronExpression = (cron: string) => {
  // 简单的Cron表达式解析（示例）
  try {
    const parts = cron.split(' ')
    if (parts.length !== 5) return '格式错误'

    const [minute, hour] = parts
    const weekday = parts[4]

    if (minute === '0' && hour !== '*') {
      return `每天${hour}点执行`
    }
    if (weekday !== '*') {
      const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
      return `每${weekdays[parseInt(weekday) % 7]}执行`
    }

    return '已配置'
  } catch {
    return '解析失败'
  }
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const response = await scheduledTasksApi.getScheduledTasks({
      page: pagination.page,
      page_size: pagination.pageSize,
    })
    // 将ScheduledTaskListItem转换为ScheduledTask格式
    scheduledTasks.value = response.items.map((task: ScheduledTaskListItem) => ({
      ...task,
      config_json: (task as ScheduledTask).config_json || ({} as CrawlTaskConfig),
      _toggling: false,
    }))
    pagination.total = response.total || 0
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '获取定时任务列表失败')
  } finally {
    loading.value = false
  }
}

const handleSizeChange = () => {
  pagination.page = 1
  fetchTasks()
}

const handlePageChange = () => {
  fetchTasks()
}

const handleToggle = async (task: ScheduledTask & { _toggling: boolean }) => {
  task._toggling = true
  try {
    await scheduledTasksApi.toggleScheduledTask(task.id, task.is_enabled)
    ElMessage.success(task.is_enabled ? '任务已启用' : '任务已禁用')
    await fetchTasks()
  } catch (error) {
    task.is_enabled = !task.is_enabled
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '操作失败')
  } finally {
    task._toggling = false
  }
}

const handleEdit = (task: ScheduledTask) => {
  editingTask.value = task
  const config = task.config_json as CrawlTaskConfig | BackupTaskConfig | undefined
  Object.assign(taskForm, {
    task_type: task.task_type,
    task_name: task.task_name,
    cron_expression: task.cron_expression,
    keywords: (config as CrawlTaskConfig)?.keywords?.join(',') || '',
    backup_type: (config as BackupTaskConfig)?.backup_type || 'full',
    is_enabled: task.is_enabled,
  })
  showCreateDialog.value = true
}

const handleDelete = async (task: ScheduledTask) => {
  try {
    await ElMessageBox.confirm('确定要删除这个定时任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await scheduledTasksApi.deleteScheduledTask(task.id)
    ElMessage.success('任务已删除')
    await fetchTasks()
  } catch (error) {
    // ElMessageBox.confirm 取消时会抛出 'cancel' 字符串
    if (typeof error === 'string' && error === 'cancel') {
      return
    }
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '删除任务失败')
  }
}

const handleCancelDialog = () => {
  showCreateDialog.value = false
  editingTask.value = null
  Object.assign(taskForm, {
    task_type: 'crawl_task',
    task_name: '',
    cron_expression: '0 2 * * *',
    keywords: '',
    backup_type: 'full',
    is_enabled: true,
  })
}

const handleSave = async () => {
  if (!taskFormRef.value) return

  await taskFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      saving.value = true
      try {
        let config: CrawlTaskConfig | BackupTaskConfig
        if (taskForm.task_type === 'crawl_task') {
          config = {} as CrawlTaskConfig
          if (taskForm.keywords.trim()) {
            config.keywords = taskForm.keywords.split(',').map((k) => k.trim()).filter(Boolean)
          }
        } else {
          config = { backup_type: taskForm.backup_type } as BackupTaskConfig
        }

        const request: ScheduledTaskCreateRequest = {
          task_type: taskForm.task_type,
          task_name: taskForm.task_name,
          cron_expression: taskForm.cron_expression,
          config,  // 后端要求config字段必需，即使是空对象也要提供
          is_enabled: taskForm.is_enabled,
        }

        if (editingTask.value) {
          await scheduledTasksApi.updateScheduledTask(editingTask.value.id, request)
          ElMessage.success('任务已更新')
        } else {
          await scheduledTasksApi.createScheduledTask(request)
          ElMessage.success('任务已创建')
        }

        handleCancelDialog()
        await fetchTasks()
      } catch (error) {
        const apiError = error as ApiError
        ElMessage.error(apiError.response?.data?.detail || '保存失败')
      } finally {
        saving.value = false
      }
    }
  })
}

onMounted(() => {
  fetchTasks()
})
</script>

<style lang="scss" scoped>
.scheduled-tasks-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    h2 {
      margin: 0;
      font-size: 20px;
    }
  }

  .cron-help-text {
    margin-top: 5px;
    font-size: 12px;
    color: #909399;

    .cron-preview {
      margin: 0;
      color: #409eff;
    }
  }

  .cron-help {
    ul {
      margin: 10px 0;
      padding-left: 20px;

      li {
        margin: 5px 0;

        code {
          background-color: #f5f7fa;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: monospace;
        }
      }
    }
  }
}

.scheduled-tasks-page {
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
  
  // 分页器
  :deep(.el-pagination) {
    margin-top: 20px;
    justify-content: flex-end;
    flex-wrap: wrap;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .scheduled-tasks-page {
    .card-header {
      h2 {
        font-size: 18px;
      }
    }
  }
}
</style>

