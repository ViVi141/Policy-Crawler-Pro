<template>
  <div class="tasks-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>任务管理</h2>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            创建任务
          </el-button>
        </div>
      </template>

      <!-- 筛选 -->
      <el-form :model="filterForm" inline class="filter-form">
        <el-form-item label="任务类型">
          <el-select v-model="filterForm.task_type" placeholder="全部类型" clearable>
            <el-option label="爬取任务" value="crawl_task" />
            <el-option label="备份任务" value="backup_task" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="全部状态" clearable>
            <el-option label="待执行" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchTasks">筛选</el-button>
          <el-button @click="handleResetFilter">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 任务列表 -->
      <el-table v-loading="loading" :data="tasks" stripe style="width: 100%">
        <el-table-column prop="task_name" label="任务名称" min-width="200" />
        <el-table-column prop="task_type" label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.task_type === 'crawl_task' ? 'primary' : 'success'">
              {{ row.task_type === 'crawl_task' ? '爬取任务' : '备份任务' }}
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
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :status="getProgressStatus(row.status)" />
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ row.started_at ? formatDateTime(row.started_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ row.completed_at ? formatDateTime(row.completed_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleViewDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 'completed' && row.task_type === 'crawl_task'"
              link
              type="success"
              @click="handleDownloadTaskFiles(row)"
            >
              下载文件
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              link
              type="warning"
              @click="handlePause(row)"
            >
              暂停
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              link
              type="danger"
              @click="handleCancel(row)"
            >
              取消
            </el-button>
            <el-button
              v-if="row.status === 'paused'"
              link
              type="primary"
              @click="handleResume(row)"
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

    <!-- 下载格式选择对话框 -->
    <el-dialog
      v-model="downloadFormatDialog"
      title="选择下载格式"
      width="400px"
    >
      <el-form label-width="120px">
        <el-form-item label="文件格式">
          <el-select v-model="downloadFormat" style="width: 100%">
            <el-option label="全部格式（Markdown + DOCX）" value="all" />
            <el-option label="仅 Markdown" value="markdown" />
            <el-option label="仅 DOCX" value="docx" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="downloadFormatDialog = false">取消</el-button>
          <el-button type="primary" @click="confirmDownload">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 创建任务对话框 -->
    <el-dialog 
      v-model="showCreateDialog" 
      title="创建任务" 
      width="600px"
      @opened="handleDialogOpened"
    >
      <el-form :model="taskForm" :rules="taskRules" ref="taskFormRef" label-width="100px">
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="taskForm.task_type" placeholder="请选择任务类型" @change="handleTaskTypeChange">
            <el-option label="爬取任务" value="crawl_task" />
            <el-option label="备份任务" value="backup_task" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="taskForm.task_name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item v-if="taskForm.task_type === 'crawl_task'" label="关键词">
          <el-input
            v-model="taskForm.keywords"
            type="textarea"
            :rows="3"
            placeholder="多个关键词用逗号分隔，留空表示爬取全部"
          />
          <div class="help-text">
            留空表示全量爬取（不限制关键词）。如果同时留空关键词和日期范围，将爬取所有政策。
          </div>
        </el-form-item>
        <el-form-item v-if="taskForm.task_type === 'crawl_task'" label="日期范围">
          <el-date-picker
            v-model="taskForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
          />
          <div class="help-text">
            留空表示不限制时间范围。如果同时留空关键词和日期范围，将进行全量爬取。
          </div>
        </el-form-item>
        <el-form-item v-if="taskForm.task_type === 'crawl_task'" label="最大页数">
          <el-input-number
            v-model="taskForm.limitPages"
            :min="1"
            :max="1000"
            placeholder="留空表示不限制"
          />
          <span class="help-text">限制爬取的页面数量，留空表示不限制</span>
        </el-form-item>
        <el-form-item 
          v-if="taskForm.task_type === 'crawl_task'" 
          label="数据源" 
          prop="selectedDataSources"
          required
        >
          <el-checkbox-group v-model="taskForm.selectedDataSources">
            <el-checkbox
              v-for="source in availableDataSources"
              :key="source.name"
              :label="source.name"
              :disabled="false"
            >
              {{ source.name }}
              <el-tag v-if="source.enabled" type="success" size="small" style="margin-left: 8px;">已启用</el-tag>
            </el-checkbox>
          </el-checkbox-group>
          <div class="help-text" style="margin-top: 8px; color: #909399; font-size: 12px;">
            <div>• 必须至少选择一个数据源</div>
            <div>• 可以选择一个或两个数据源。如果选择两个，将按顺序执行：先完成第一个数据源的所有分类，再执行第二个数据源。</div>
            <div v-if="availableDataSources.length === 0" style="color: #f56c6c; margin-top: 5px;">
              ⚠️ 当前没有可用的数据源，请先在系统设置中配置数据源
            </div>
          </div>
        </el-form-item>
        <el-form-item v-if="taskForm.task_type === 'backup_task'" label="备份类型">
          <el-select v-model="taskForm.backup_type" placeholder="请选择备份类型">
            <el-option label="完整备份" value="full" />
            <el-option label="增量备份" value="incremental" />
          </el-select>
        </el-form-item>
        <el-form-item label="自动启动">
          <el-switch v-model="taskForm.autoStart" />
          <span class="help-text">创建后立即开始执行任务</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 任务详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="任务详情" width="900px" @close="stopTaskDetailRefresh">
      <div v-if="currentTask" class="task-detail">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <el-tab-pane label="基本信息" name="info">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="任务名称">{{ currentTask.task_name }}</el-descriptions-item>
              <el-descriptions-item label="任务类型">
                {{ currentTask.task_type === 'crawl_task' ? '爬取任务' : '备份任务' }}
              </el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="getStatusType(currentTask.status)">
                  {{ getStatusText(currentTask.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="进度">
                <el-progress :percentage="currentTask.progress" :status="getProgressStatus(currentTask.status)" />
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ currentTask.created_at ? formatDateTime(currentTask.created_at) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="开始时间">
                {{ (currentTask.started_at || currentTask.start_time) ? formatDateTime((currentTask.started_at || currentTask.start_time || '')) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="完成时间">
                {{ (currentTask.completed_at || currentTask.end_time) ? formatDateTime((currentTask.completed_at || currentTask.end_time || '')) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="执行时长">
                {{ getDuration(currentTask.started_at || currentTask.start_time, currentTask.completed_at || currentTask.end_time) }}
              </el-descriptions-item>
              <el-descriptions-item v-if="currentTask.task_type === 'crawl_task'" label="统计信息" :span="2">
                <div class="stats">
                  <div class="stat-item">
                    <div class="stat-label">政策总数</div>
                    <div class="stat-value">{{ currentTask.result_json?.policy_count || currentTask.policy_count || 0 }}</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-label">成功保存</div>
                    <div class="stat-value" style="color: #67c23a">{{ currentTask.result_json?.success_count || currentTask.success_count || 0 }}</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-label">失败数量</div>
                    <div class="stat-value" style="color: #f56c6c">{{ currentTask.result_json?.failed_count || currentTask.failed_count || 0 }}</div>
                  </div>
                </div>
              </el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
          
          <el-tab-pane label="任务配置" name="config">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="配置信息">
                <pre class="config-json">{{ JSON.stringify(currentTask.config_json, null, 2) }}</pre>
              </el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
          
          <el-tab-pane label="执行结果" name="result">
            <div v-if="currentTask.result_json">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="政策总数">
                  {{ currentTask.result_json.policy_count || 0 }}
                </el-descriptions-item>
                <el-descriptions-item label="成功保存">
                  <span style="color: #67c23a">{{ currentTask.result_json.success_count || 0 }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="跳过数量">
                  <span style="color: #909399">{{ currentTask.result_json.skipped_count || 0 }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="失败数量">
                  <span style="color: #f56c6c">{{ currentTask.result_json.failed_count || 0 }}</span>
                </el-descriptions-item>
              </el-descriptions>
              <div v-if="currentTask.result_json.message" style="margin-top: 20px">
                <el-alert :title="currentTask.result_json.message" type="info" :closable="false" />
              </div>
            </div>
            <el-empty v-else description="暂无执行结果" />
          </el-tab-pane>
          
          <el-tab-pane v-if="currentTask.status === 'running' || currentTask.progress_message" label="实时进度" name="progress">
            <div class="progress-log-container">
              <div class="progress-log-header">
                <span>任务执行日志</span>
                <div>
                  <el-tag v-if="currentTask.status === 'running'" type="success" size="small">运行中</el-tag>
                  <el-tag v-else-if="currentTask.status === 'completed'" type="success" size="small">已完成</el-tag>
                  <el-tag v-else-if="currentTask.status === 'failed'" type="danger" size="small">失败</el-tag>
                  <el-tag v-else-if="currentTask.status === 'paused'" type="warning" size="small">已暂停</el-tag>
                  <el-tag v-else-if="currentTask.status === 'cancelled'" type="info" size="small">已取消</el-tag>
                </div>
              </div>
              <div class="progress-log-content" ref="progressLogContentRef">
                <pre v-if="currentTask.progress_message" class="progress-log">{{ currentTask.progress_message }}</pre>
                <el-empty v-else description="暂无进度信息" />
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane v-if="currentTask.error_message" label="错误信息" name="error">
            <el-alert type="error" :closable="false">
              <pre class="error-message">{{ currentTask.error_message }}</pre>
            </el-alert>
          </el-tab-pane>
        </el-tabs>
        
        <div class="task-actions" style="margin-top: 20px; text-align: right">
          <el-button v-if="currentTask.status === 'pending'" type="primary" @click="handleStartTask(currentTask)">
            启动任务
          </el-button>
          <el-button v-if="currentTask.status === 'running'" type="warning" @click="handlePause(currentTask)">
            暂停任务
          </el-button>
          <el-button v-if="currentTask.status === 'running'" type="danger" @click="handleCancel(currentTask)">
            取消任务
          </el-button>
          <el-button v-if="currentTask.status === 'paused'" type="primary" @click="handleResume(currentTask)">
            恢复任务
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { tasksApi, type TaskListParams } from '../api/tasks'
import { configApi } from '../api/config'
import type { Task, TaskCreateRequest } from '../types/task'
import type { ApiError, CrawlTaskConfig, BackupTaskConfig, DataSourceConfig } from '../types/common'
import type { FormInstance, FormRules } from 'element-plus'
import dayjs from 'dayjs'

const loading = ref(false)
const creating = ref(false)
const tasks = ref<Task[]>([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const currentTask = ref<Task | null>(null)
const taskFormRef = ref<FormInstance>()
const activeTab = ref('info')
const progressLogContentRef = ref<HTMLElement | null>(null)
let taskDetailRefreshInterval: ReturnType<typeof setInterval> | null = null

const filterForm = reactive({
  task_type: '',
  status: '',
})

const availableDataSources = ref<DataSourceConfig[]>([])
const taskForm = reactive<{
  task_type: string
  task_name: string
  keywords: string
  backup_type: string
  dateRange: [string, string] | null
  limitPages: number | null
  autoStart: boolean
  selectedDataSources: string[]
}>({
  task_type: 'crawl_task',
  task_name: '',
  keywords: '',
  backup_type: 'full',
  dateRange: null,
  limitPages: null,
  autoStart: true,
  selectedDataSources: [],
})

const taskRules: FormRules = {
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  selectedDataSources: [
    {
      validator: (_rule: unknown, value: string[], callback: (error?: Error) => void) => {
        // 对于爬取任务，必须至少选择一个数据源
        if (taskForm.task_type === 'crawl_task') {
          if (!value || value.length === 0) {
            callback(new Error('请至少选择一个数据源'))
            return
          }
        }
        callback()
      },
      trigger: 'change',
    },
  ],
}

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    paused: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待执行',
    running: '运行中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return statusMap[status] || status
}

const getProgressStatus = (status: string): 'success' | 'exception' | undefined => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'running') return undefined
  return undefined
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const params: TaskListParams = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filterForm.task_type) params.task_type = filterForm.task_type
    if (filterForm.status) params.status = filterForm.status

    const response = await tasksApi.getTasks(params)
    tasks.value = response.items
    pagination.total = response.total
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const handleResetFilter = () => {
  filterForm.task_type = ''
  filterForm.status = ''
  fetchTasks()
}

const handleSizeChange = () => {
  fetchTasks()
}

const handlePageChange = () => {
  fetchTasks()
}

const handleCreate = async () => {
  if (!taskFormRef.value) return

  await taskFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      // 验证数据源选择
      if (taskForm.task_type === 'crawl_task' && taskForm.selectedDataSources.length === 0) {
        ElMessage.warning('请至少选择一个数据源')
        return
      }

      creating.value = true
      try {
        let config: CrawlTaskConfig | BackupTaskConfig
        if (taskForm.task_type === 'crawl_task') {
          config = {} as CrawlTaskConfig
          if (taskForm.keywords.trim()) {
            config.keywords = taskForm.keywords.split(',').map((k) => k.trim()).filter(Boolean)
          }
          if (taskForm.dateRange && taskForm.dateRange.length === 2) {
            config.date_range = {
              start: taskForm.dateRange[0],
              end: taskForm.dateRange[1],
            }
          }
          if (taskForm.limitPages) {
            config.limit_pages = taskForm.limitPages
          }
          // 添加数据源配置
          if (taskForm.selectedDataSources.length > 0) {
            config.data_sources = availableDataSources.value
              .filter((source: DataSourceConfig) => taskForm.selectedDataSources.includes(source.name))
              .map((source: DataSourceConfig) => ({
                ...source,
                enabled: true
              }))
          }
        } else {
          config = { backup_type: taskForm.backup_type } as BackupTaskConfig
        }

        const request: TaskCreateRequest = {
          task_type: taskForm.task_type,
          task_name: taskForm.task_name,
          config,
        }

        await tasksApi.createTask(request, taskForm.autoStart)
        ElMessage.success('任务创建成功')
        showCreateDialog.value = false
        // 重置表单，但保留数据源选择和任务类型
        const defaultSelectedDataSources = availableDataSources.value.length > 0 
          ? [availableDataSources.value.find(ds => ds.enabled)?.name || availableDataSources.value[0].name].filter(Boolean)
          : []
        Object.assign(taskForm, {
          task_type: 'crawl_task',
          task_name: '',
          keywords: '',
          backup_type: 'full',
          dateRange: null,
          limitPages: null,
          autoStart: true,
          selectedDataSources: defaultSelectedDataSources,
        })
        fetchTasks()
      } catch (error) {
        const apiError = error as ApiError
        ElMessage.error(apiError.response?.data?.detail || '创建任务失败')
      } finally {
        creating.value = false
      }
    }
  })
}

const handleViewDetail = async (task: Task) => {
  try {
    currentTask.value = await tasksApi.getTaskById(task.id)
    showDetailDialog.value = true
    
    // 如果任务正在运行，自动切换到进度标签页并开始刷新
    if (task.status === 'running') {
      activeTab.value = 'progress'
      startTaskDetailRefresh(task.id)
    } else {
      activeTab.value = 'info'
    }
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '获取任务详情失败')
  }
}

const handleTabChange = (tabName: string) => {
  // 切换到进度标签页时，如果是运行中的任务，确保开始刷新
  if (tabName === 'progress' && currentTask.value?.status === 'running') {
    if (currentTask.value) {
      startTaskDetailRefresh(currentTask.value.id)
      // 滚动到底部显示最新进度
      scrollToBottom()
    }
  }
}

const scrollToBottom = () => {
  // 自动滚动进度日志到底部
  nextTick(() => {
    if (progressLogContentRef.value) {
      progressLogContentRef.value.scrollTop = progressLogContentRef.value.scrollHeight
    }
  })
}

const startTaskDetailRefresh = (taskId: number) => {
  stopTaskDetailRefresh()
  taskDetailRefreshInterval = setInterval(async () => {
    try {
      const updated = await tasksApi.getTaskById(taskId)
      if (currentTask.value) {
        const oldProgressMessage = currentTask.value.progress_message
        Object.assign(currentTask.value, updated)
        // 如果进度消息有更新且正在查看进度标签页，滚动到底部
        if (updated.progress_message && updated.progress_message !== oldProgressMessage && activeTab.value === 'progress') {
          scrollToBottom()
        }
        // 如果任务已完成或失败，停止刷新
        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'cancelled' || updated.status === 'paused') {
          stopTaskDetailRefresh()
        }
      }
    } catch (error) {
      console.error('刷新任务详情失败:', error)
      stopTaskDetailRefresh()
    }
  }, 2000)
}

// 监听进度消息变化，自动滚动到底部
watch(() => currentTask.value?.progress_message, () => {
  if (activeTab.value === 'progress') {
    scrollToBottom()
  }
})

const stopTaskDetailRefresh = () => {
  if (taskDetailRefreshInterval) {
    clearInterval(taskDetailRefreshInterval)
    taskDetailRefreshInterval = null
  }
}

const handleStartTask = async (task: Task) => {
  try {
    await tasksApi.startTask(task.id)
    ElMessage.success('任务已启动')
    await handleViewDetail(task)
    fetchTasks()
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '启动任务失败')
  }
}

const getDuration = (start: string | undefined, end: string | undefined) => {
  if (!start) return '-'
  const endTime = end ? dayjs(end) : dayjs()
  const duration = endTime.diff(dayjs(start), 'second')
  if (duration < 60) return `${duration}秒`
  if (duration < 3600) return `${Math.floor(duration / 60)}分${duration % 60}秒`
  return `${Math.floor(duration / 3600)}小时${Math.floor((duration % 3600) / 60)}分`
}

const handlePause = async (task: Task) => {
  try {
    await ElMessageBox.confirm('确定要暂停这个任务吗？暂停后可以恢复。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await tasksApi.pauseTask(task.id)
    ElMessage.success('任务已暂停')
    if (currentTask.value && currentTask.value.id === task.id) {
      await handleViewDetail(task)
    }
    fetchTasks()
  } catch (error) {
    if (typeof error === 'string' && error === 'cancel') {
      return
    }
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '暂停任务失败')
  }
}

const handleResume = async (task: Task) => {
  try {
    await tasksApi.resumeTask(task.id)
    ElMessage.success('任务已恢复')
    if (currentTask.value && currentTask.value.id === task.id) {
      await handleViewDetail(task)
    }
    fetchTasks()
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '恢复任务失败')
  }
}

const handleCancel = async (task: Task) => {
  try {
    await ElMessageBox.confirm('确定要取消这个任务吗？取消后将无法恢复。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await tasksApi.stopTask(task.id)
    ElMessage.success('任务已取消')
    if (currentTask.value && currentTask.value.id === task.id) {
      await handleViewDetail(task)
    }
    fetchTasks()
  } catch (error) {
    if (typeof error === 'string' && error === 'cancel') {
      return
    }
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '取消任务失败')
  }
}

const downloadFormatDialog = ref(false)
const downloadFormat = ref<'all' | 'markdown' | 'docx'>('all')
const downloadingTask = ref<Task | null>(null)

const handleDownloadTaskFiles = async (task: Task) => {
  // 显示格式选择对话框
  downloadingTask.value = task
  downloadFormat.value = 'all'
  downloadFormatDialog.value = true
}

const confirmDownload = async () => {
  if (!downloadingTask.value) {
    return
  }
  
  downloadFormatDialog.value = false
  
  try {
    ElMessage.info('正在打包文件，请稍候...')
    
    // 调用下载API
    const blob = await tasksApi.downloadTaskFiles(downloadingTask.value.id, downloadFormat.value)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // 生成文件名
    const timestamp = dayjs().format('YYYYMMDD_HHmmss')
    const formatSuffix = downloadFormat.value === 'all' ? 'all' : downloadFormat.value
    link.download = `${downloadingTask.value.task_name}_${formatSuffix}_${timestamp}.zip`
    
    // 触发下载
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // 释放URL对象
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('文件下载成功')
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '下载文件失败')
  } finally {
    downloadingTask.value = null
  }
}

const handleDelete = async (task: Task) => {
  try {
    const message = task.status === 'running' 
      ? '任务正在运行中，删除前将自动停止。确定要删除这个任务吗？' 
      : '确定要删除这个任务吗？删除后将无法恢复。'
    
    await ElMessageBox.confirm(message, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await tasksApi.deleteTask(task.id)
    ElMessage.success('任务已删除')
    if (showDetailDialog.value && currentTask.value?.id === task.id) {
      showDetailDialog.value = false
    }
    fetchTasks()
  } catch (error) {
    if (typeof error === 'string' && error === 'cancel') {
      return
    }
    const apiError = error as ApiError
    ElMessage.error(apiError.response?.data?.detail || '删除任务失败')
  }
}

let refreshInterval: ReturnType<typeof setInterval> | null = null

const loadDataSources = async () => {
  try {
    const response = await configApi.getDataSources()
    availableDataSources.value = response.data_sources
    // 默认选择第一个启用的数据源，如果没有启用的则选择第一个
    const enabledSource = response.data_sources.find(ds => ds.enabled)
    if (enabledSource) {
      taskForm.selectedDataSources = [enabledSource.name]
    } else if (response.data_sources.length > 0) {
      taskForm.selectedDataSources = [response.data_sources[0].name]
    }
  } catch (error) {
    const apiError = error as ApiError
    ElMessage.warning(apiError.response?.data?.detail || '获取数据源列表失败，将使用默认配置')
    // 使用默认数据源
    availableDataSources.value = [
      {
        name: '政府信息公开平台',
        base_url: 'https://gi.mnr.gov.cn/',
        search_api: 'https://search.mnr.gov.cn/was5/web/search',
        ajax_api: 'https://search.mnr.gov.cn/was/ajaxdata_jsonp.jsp',
        channel_id: '216640',
        enabled: true,
      },
      {
        name: '政策法规库',
        base_url: 'https://f.mnr.gov.cn/',
        search_api: 'https://search.mnr.gov.cn/was5/web/search',
        ajax_api: 'https://search.mnr.gov.cn/was/ajaxdata_jsonp.jsp',
        channel_id: '174757',
        enabled: false,
      },
    ]
    taskForm.selectedDataSources = ['政府信息公开平台']
  }
}

const handleTaskTypeChange = () => {
  // 当任务类型切换时，如果是爬取任务，确保有数据源选择
  if (taskForm.task_type === 'crawl_task' && availableDataSources.value.length > 0) {
    if (taskForm.selectedDataSources.length === 0) {
      const enabledSource = availableDataSources.value.find(ds => ds.enabled)
      if (enabledSource) {
        taskForm.selectedDataSources = [enabledSource.name]
      } else if (availableDataSources.value.length > 0) {
        taskForm.selectedDataSources = [availableDataSources.value[0].name]
      }
    }
  } else {
    // 切换到备份任务时，清空数据源选择
    taskForm.selectedDataSources = []
  }
}

const handleDialogOpened = async () => {
  // 对话框打开时，重新加载数据源列表以获取最新的启用状态
  await loadDataSources()
  // 如果是爬取任务，确保有数据源选择
  if (taskForm.task_type === 'crawl_task' && availableDataSources.value.length > 0) {
    // 如果没有选择数据源，默认选择第一个启用的
    if (taskForm.selectedDataSources.length === 0) {
      const enabledSource = availableDataSources.value.find(ds => ds.enabled)
      if (enabledSource) {
        taskForm.selectedDataSources = [enabledSource.name]
      } else if (availableDataSources.value.length > 0) {
        taskForm.selectedDataSources = [availableDataSources.value[0].name]
      }
    }
  }
}

onMounted(() => {
  loadDataSources()
  fetchTasks()
  // 定时刷新任务列表
  refreshInterval = setInterval(() => {
    fetchTasks()
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  stopTaskDetailRefresh()
})
</script>

<style lang="scss" scoped>
.tasks-page {
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

  .filter-form {
    margin-bottom: 20px;
    padding: 20px;
    background-color: #f5f7fa;
    border-radius: 4px;
    
    :deep(.el-form-item) {
      margin-bottom: 10px;
    }
  }

  pre {
    background-color: #f5f7fa;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
    word-wrap: break-word;
    white-space: pre-wrap;
  }
  
  .task-detail {
    .stats {
      display: flex;
      gap: 30px;
      margin-top: 10px;
      padding: 15px;
      background-color: #f5f7fa;
      border-radius: 4px;
      
      .stat-item {
        text-align: center;
        
        .stat-label {
          font-size: 12px;
          color: #909399;
          margin-bottom: 8px;
        }
        
        .stat-value {
          font-size: 24px;
          font-weight: 600;
          color: #303133;
        }
      }
    }
    
    .config-json {
      background-color: #f5f7fa;
      padding: 15px;
      border-radius: 4px;
      overflow-x: auto;
      max-height: 400px;
      overflow-y: auto;
      font-size: 12px;
      line-height: 1.6;
    }
    
    .error-message {
      margin: 0;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
    
    .help-text {
      margin-left: 10px;
      font-size: 12px;
      color: #909399;
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
  .tasks-page {
    .filter-form {
      padding: 15px;
      
      :deep(.el-form-item) {
        width: 100%;
        margin-right: 0;
      }
    }
    
    .card-header {
      h2 {
        font-size: 18px;
      }
    }
  }
}
</style>

