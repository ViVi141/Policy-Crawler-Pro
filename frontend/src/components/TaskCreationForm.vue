<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="700px"
    @opened="handleDialogOpened"
    @closed="handleDialogClosed"
  >
    <el-form
      :model="formData"
      :rules="formRules"
      ref="formRef"
      label-width="120px"
      class="task-form"
    >
      <!-- 任务类型选择 -->
      <el-form-item label="任务类型" prop="task_type">
        <el-select
          v-model="formData.task_type"
          placeholder="请选择任务类型"
          @change="handleTaskTypeChange"
          :disabled="mode === 'edit' || disableTaskTypeSelect"
        >
          <el-option label="爬取任务" value="crawl_task" />
          <el-option label="备份任务" value="backup_task" />
          <el-option label="定时任务" value="scheduled_task" />
        </el-select>
      </el-form-item>

      <!-- 任务名称 -->
      <el-form-item label="任务名称" prop="task_name">
        <el-input v-model="formData.task_name" placeholder="请输入任务名称" />
      </el-form-item>

      <!-- 定时任务专用字段 -->
      <template v-if="formData.task_type === 'scheduled_task'">
        <el-form-item label="Cron表达式" prop="cron_expression">
          <div class="cron-input-group">
            <el-input
              v-model="formData.cron_expression"
              placeholder="例如: 0 2 * * * (每天凌晨2点)"
              class="cron-input"
            />
            <el-button @click="showCronSelector = true" type="primary">
              <el-icon><Setting /></el-icon>
              可视化配置
            </el-button>
          </div>
          <div class="cron-help-text" v-if="formData.cron_expression">
            <p class="cron-preview">
              预览: {{ parseCronExpression(formData.cron_expression) }}
            </p>
            <p class="next-run-time" v-if="nextRunTime">
              下次运行时间: {{ nextRunTime }}
            </p>
          </div>
        </el-form-item>
      </template>

      <!-- 爬取任务配置 -->
      <template v-if="formData.task_type === 'crawl_task' || (formData.task_type === 'scheduled_task' && formData.scheduled_task_type === 'crawl_task')">
        <el-form-item label="关键词">
          <el-input
            v-model="crawlConfig.keywords"
            type="textarea"
            :rows="3"
            placeholder="多个关键词用逗号分隔，留空表示爬取全部"
          />
          <div class="help-text">
            留空表示全量爬取（不限制关键词）。如果同时留空关键词和日期范围，将爬取所有政策。
          </div>
        </el-form-item>

        <el-form-item label="日期范围">
          <el-date-picker
            v-model="crawlConfig.dateRange"
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

        <el-form-item label="最大页数">
          <el-input-number
            v-model="crawlConfig.limitPages"
            :min="1"
            :max="1000"
            placeholder="留空表示不限制"
          />
          <span class="help-text">限制爬取的页面数量，留空表示不限制</span>
        </el-form-item>

        <el-form-item label="数据源" prop="crawlConfig.selectedDataSources">
          <el-checkbox-group v-model="crawlConfig.selectedDataSources">
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
      </template>

      <!-- 备份任务配置 -->
      <template v-if="formData.task_type === 'backup_task' || (formData.task_type === 'scheduled_task' && formData.scheduled_task_type === 'backup_task')">
        <el-form-item label="备份类型">
          <el-select v-model="backupConfig.backup_type" placeholder="请选择备份类型">
            <el-option label="完整备份" value="full" />
            <el-option label="增量备份" value="incremental" />
          </el-select>
        </el-form-item>

        <el-form-item label="保留策略">
          <el-select v-model="backupConfig.retention_policy" placeholder="请选择保留策略">
            <el-option label="保留所有备份" value="keep_all" />
            <el-option label="保留最近7天的备份" value="keep_7_days" />
            <el-option label="保留最近30天的备份" value="keep_30_days" />
            <el-option label="保留最近90天的备份" value="keep_90_days" />
            <el-option label="保留最近10个备份" value="keep_10_backups" />
            <el-option label="保留最近50个备份" value="keep_50_backups" />
          </el-select>
        </el-form-item>

        <el-form-item label="压缩选项">
          <el-radio-group v-model="backupConfig.compression">
            <el-radio label="gzip">GZIP压缩</el-radio>
            <el-radio label="none">不压缩</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="包含数据">
          <el-checkbox-group v-model="backupConfig.include_data">
            <el-checkbox label="database">数据库</el-checkbox>
            <el-checkbox label="files">文件数据</el-checkbox>
            <el-checkbox label="config">配置文件</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </template>

      <!-- 定时任务专用配置 -->
      <template v-if="formData.task_type === 'scheduled_task'">
        <el-form-item label="任务内容类型" prop="scheduled_task_type">
          <el-select v-model="formData.scheduled_task_type" placeholder="请选择要定时执行的任务类型" @change="handleScheduledTaskTypeChange">
            <el-option label="爬取任务" value="crawl_task" />
            <el-option label="备份任务" value="backup_task" />
          </el-select>
        </el-form-item>

        <el-form-item label="是否启用">
          <el-switch v-model="formData.is_enabled" />
          <span class="help-text">创建后是否立即启用定时任务</span>
        </el-form-item>
      </template>

      <!-- 即时任务的自动启动选项 -->
      <template v-else>
        <el-form-item label="自动启动">
          <el-switch v-model="formData.autoStart" />
          <span class="help-text">创建后立即开始执行任务</span>
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        {{ mode === 'edit' ? '更新' : '创建' }}
      </el-button>
    </template>

    <!-- Cron表达式可视化选择器 -->
    <el-dialog
      v-model="showCronSelector"
      title="Cron表达式可视化配置"
      width="800px"
      append-to-body
    >
      <CronSelector
        v-model="formData.cron_expression"
        @confirm="handleCronConfirm"
        @cancel="showCronSelector = false"
      />
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'
import CronSelector from './CronSelector.vue'
import { configApi } from '../api/config'
import type { FormInstance, FormRules } from 'element-plus'
import type { Task } from '../types/task'
import type { ScheduledTask } from '../types/scheduledTask'
import type { TaskConfig } from '../types/common'

// 任务表单数据类型
interface TaskFormData {
  task_type: string
  task_name: string
  cron_expression?: string
  scheduled_task_type?: string
  is_enabled?: boolean
  autoStart?: boolean
  config?: CrawlTaskConfig | BackupTaskConfig
  [key: string]: unknown // 其他动态字段
}

interface ScheduledTaskFormData {
  scheduled_task_type: string
  task_name: string
  cron_expression: string
  config: TaskConfig
  is_enabled: boolean
}
import type { CrawlTaskConfig, BackupTaskConfig } from '../types/common'
import type { DataSourceConfig } from '../types/common'

// Props
interface Props {
  modelValue: boolean
  mode?: 'create' | 'edit'
  taskType?: 'crawl_task' | 'backup_task' | 'scheduled_task'
  editData?: Task | ScheduledTask
  disableTaskTypeSelect?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'create',
  taskType: undefined,
  disableTaskTypeSelect: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'submit': [formData: TaskFormData | ScheduledTaskFormData]
  'cancel': []
}>()

// 响应式数据
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const formRef = ref<FormInstance>()
const loading = ref(false)
const showCronSelector = ref(false)
const availableDataSources = ref<DataSourceConfig[]>([])

// 表单数据
const formData = reactive({
  task_type: props.taskType || 'crawl_task',
  task_name: '',
  cron_expression: '0 2 * * *',
  scheduled_task_type: 'crawl_task',
  is_enabled: true,
  autoStart: true
})

// 爬取任务配置
const crawlConfig = reactive({
  keywords: '',
  dateRange: null as [string, string] | null,
  limitPages: null as number | null,
  selectedDataSources: [] as string[]
})

// 备份任务配置
const backupConfig = reactive({
  backup_type: 'full',
  retention_policy: 'keep_30_days',
  compression: 'gzip',
  include_data: ['database', 'files', 'config']
})

// 表单验证规则
const formRules = computed((): FormRules => ({
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  cron_expression: props.taskType === 'scheduled_task' ? [
    { required: true, message: '请输入Cron表达式', trigger: 'blur' },
    {
      pattern: /^(\*|([0-9]|[1-5][0-9])|\*\/([0-9]|[1-5][0-9])) (\*|([0-9]|1[0-9]|2[0-3])|\*\/([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|[12][0-9]|3[01])|\*\/([1-9]|[12][0-9]|3[01])) (\*|([1-9]|1[0-2])|\*\/([1-9]|1[0-2])) (\*|([0-7])|\*\/([0-7]))$/,
      message: 'Cron表达式格式不正确',
      trigger: 'blur',
    },
  ] : [],
  scheduled_task_type: props.taskType === 'scheduled_task' ? [
    { required: true, message: '请选择任务内容类型', trigger: 'change' }
  ] : [],
  'crawlConfig.selectedDataSources': [
    {
      validator: (_rule: unknown, _value: string[], callback: (error?: Error) => void) => {
        // 移除了字段级验证，改为在提交时验证
        callback()
      },
      trigger: 'blur',
    },
  ],
}))

// 计算属性
const title = computed(() => {
  if (props.mode === 'edit') {
    return '编辑任务'
  }
  switch (formData.task_type) {
    case 'crawl_task':
      return '创建爬取任务'
    case 'backup_task':
      return '创建备份任务'
    case 'scheduled_task':
      return '创建定时任务'
    default:
      return '创建任务'
  }
})

const nextRunTime = computed(() => {
  if (!formData.cron_expression) return ''
  // 这里可以调用API来计算下次运行时间，或者使用前端库计算
  return '' // 暂时返回空，后续可以完善
})

// 方法
const parseCronExpression = (cron: string) => {
  try {
    const parts = cron.split(' ')
    if (parts.length !== 5) return '格式错误'

    const [minute, hour, day, , weekday] = parts

    if (minute === '0' && hour !== '*') {
      if (day === '*') {
        if (weekday === '*') {
          return `每天${hour}点执行`
        } else {
          const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
          const weekdayName = weekdays[parseInt(weekday) % 7]
          return `每周${weekdayName}${hour}点执行`
        }
      } else if (day !== '*') {
        return `每月${day}日${hour}点执行`
      }
    }

    if (minute === '*/30') {
      return '每30分钟执行一次'
    }
    if (minute === '*/15') {
      return '每15分钟执行一次'
    }

    return '已配置'
  } catch {
    return '解析失败'
  }
}

const handleTaskTypeChange = () => {
  // 重置相关配置
  if (formData.task_type !== 'scheduled_task') {
    formData.scheduled_task_type = 'crawl_task'
  }
}

const handleScheduledTaskTypeChange = () => {
  // 定时任务类型改变时重置对应配置
  // 这里可以添加更多的逻辑
}

const handleDialogOpened = async () => {
  await loadDataSources()

  // 如果是编辑模式，加载现有数据
  if (props.mode === 'edit' && props.editData) {
    loadEditData()
  } else {
    // 创建模式，重置表单
    resetForm()
  }
}

const handleDialogClosed = () => {
  // 对话框关闭时的清理逻辑
}

const loadDataSources = async () => {
  try {
    const response = await configApi.getDataSources()
    availableDataSources.value = response.data_sources

    // 默认选择第一个启用的数据源（仅在创建模式且没有选择时）
    if (availableDataSources.value.length > 0 && crawlConfig.selectedDataSources.length === 0 && props.mode === 'create') {
      const enabledSource = availableDataSources.value.find(ds => ds.enabled)
      if (enabledSource) {
        crawlConfig.selectedDataSources = [enabledSource.name]
      } else {
        crawlConfig.selectedDataSources = [availableDataSources.value[0].name]
      }
      console.log('创建模式下设置默认数据源:', crawlConfig.selectedDataSources)
    }
  } catch (error) {
    console.warn('获取数据源列表失败:', error)
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

    // 默认选择启用的数据源
    const enabledSource = availableDataSources.value.find(ds => ds.enabled)
    if (enabledSource) {
      crawlConfig.selectedDataSources = [enabledSource.name]
      console.log('默认选择启用数据源:', enabledSource.name)
    } else if (availableDataSources.value.length > 0) {
      crawlConfig.selectedDataSources = [availableDataSources.value[0].name]
      console.log('默认选择第一个数据源:', availableDataSources.value[0].name)
    }
  }
}

// Type guard to check if data is a ScheduledTask
const isScheduledTask = (data: Task | ScheduledTask): data is ScheduledTask => {
  return data.task_type === 'scheduled_task'
}

const loadEditData = () => {
  const data = props.editData
  if (!data) return

  // 基础信息
  formData.task_type = (data.task_type as 'crawl_task' | 'backup_task' | 'scheduled_task') || 'crawl_task'
  formData.task_name = data.task_name || ''

  // 根据任务类型加载配置
  if (isScheduledTask(data)) {
    formData.cron_expression = data.cron_expression || '0 2 * * *'
    formData.is_enabled = data.is_enabled !== false
    formData.scheduled_task_type = (data as any).scheduled_task_type || 'crawl_task'
  } else {
    formData.autoStart = true
  }

  // 加载任务配置
  const configSource = data.config_json || (data as any).config
  if (configSource) {
    const config = configSource as CrawlTaskConfig | BackupTaskConfig

    if ((formData.task_type === 'crawl_task') ||
        (formData.task_type === 'scheduled_task' && formData.scheduled_task_type === 'crawl_task')) {
      const crawlConfigData = config as CrawlTaskConfig
      crawlConfig.keywords = crawlConfigData.keywords ? crawlConfigData.keywords.join(',') : ''
      crawlConfig.dateRange = crawlConfigData.date_range ? [crawlConfigData.date_range.start || '', crawlConfigData.date_range.end || ''] : null
      crawlConfig.limitPages = crawlConfigData.limit_pages || null
      crawlConfig.selectedDataSources = crawlConfigData.data_sources ?
        crawlConfigData.data_sources.map((ds: DataSourceConfig) => ds.name) : []
    } else if ((formData.task_type === 'backup_task') ||
               (formData.task_type === 'scheduled_task' && formData.scheduled_task_type === 'backup_task')) {
      const backupConfigData = config as BackupTaskConfig
      backupConfig.backup_type = backupConfigData.backup_type || 'full'
      backupConfig.retention_policy = (backupConfigData as any).retention_policy || 'keep_30_days'
      backupConfig.compression = (backupConfigData as any).compression || 'gzip'
      backupConfig.include_data = (backupConfigData as any).include_data || ['database', 'files', 'config']
    }
  }
}

const resetForm = () => {
  Object.assign(formData, {
    task_type: props.taskType || 'crawl_task',
    task_name: '',
    cron_expression: '0 2 * * *',
    scheduled_task_type: 'crawl_task',
    is_enabled: true,
    autoStart: true
  })

  Object.assign(crawlConfig, {
    keywords: '',
    dateRange: null,
    limitPages: null,
    selectedDataSources: []
  })

  Object.assign(backupConfig, {
    backup_type: 'full',
    retention_policy: 'keep_30_days',
    compression: 'gzip',
    include_data: ['database', 'files', 'config']
  })

  // 重新选择默认数据源
  if (availableDataSources.value.length > 0) {
    const enabledSource = availableDataSources.value.find(ds => ds.enabled)
    if (enabledSource) {
      crawlConfig.selectedDataSources = [enabledSource.name]
    } else {
      crawlConfig.selectedDataSources = [availableDataSources.value[0].name]
    }

    console.log('表单重置时设置默认数据源:', crawlConfig.selectedDataSources)
  } else {
    // 如果没有可用数据源，清空选择
    crawlConfig.selectedDataSources = []
  }
}

const handleCronConfirm = (cronExpression: string) => {
  formData.cron_expression = cronExpression
  showCronSelector.value = false
}

const handleCancel = () => {
  dialogVisible.value = false
  emit('cancel')
}

const handleSubmit = async () => {
  if (!formRef.value) return

  // 首先进行表单验证
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      // 自定义验证：检查数据源选择
      const taskType = formData.task_type
      const scheduledTaskType = formData.scheduled_task_type

      // 对于爬取任务或定时爬取任务，必须至少选择一个数据源
      if ((taskType === 'crawl_task') ||
          (taskType === 'scheduled_task' && scheduledTaskType === 'crawl_task')) {
        if (!crawlConfig.selectedDataSources || crawlConfig.selectedDataSources.length === 0) {
          ElMessage.error('请至少选择一个数据源')
          return
        }
      }
      loading.value = true
      try {
        let config: CrawlTaskConfig | BackupTaskConfig

        if (formData.task_type === 'scheduled_task') {
          // 定时任务
          if (formData.scheduled_task_type === 'crawl_task') {
            config = {} as CrawlTaskConfig
            if (crawlConfig.keywords.trim()) {
              config.keywords = crawlConfig.keywords.split(',').map((k: string) => k.trim()).filter(Boolean)
            }
            if (crawlConfig.dateRange && crawlConfig.dateRange.length === 2) {
              config.date_range = {
                start: crawlConfig.dateRange[0],
                end: crawlConfig.dateRange[1],
              }
            }
            if (crawlConfig.limitPages) {
              config.limit_pages = crawlConfig.limitPages
            }
            if (crawlConfig.selectedDataSources.length > 0) {
              const filteredSources = availableDataSources.value
                .filter((source: DataSourceConfig) => crawlConfig.selectedDataSources.includes(source.name))

              console.log('定时任务数据源过滤结果:', {
                selected: crawlConfig.selectedDataSources,
                available: availableDataSources.value.map(s => s.name),
                filtered: filteredSources.map(s => s.name)
              })

              config.data_sources = filteredSources
                .map((source: DataSourceConfig) => ({
                  ...source,
                  enabled: true
                }))

              console.log('定时任务最终数据源配置:', config.data_sources)
            } else {
              console.warn('警告: 定时任务没有选择数据源')
            }
          } else {
            config = {
              backup_type: backupConfig.backup_type,
              retention_policy: backupConfig.retention_policy,
              compression: backupConfig.compression,
              include_data: backupConfig.include_data
            } as BackupTaskConfig
          }

          const scheduledSubmitData: ScheduledTaskFormData = {
            scheduled_task_type: formData.scheduled_task_type,
            task_name: formData.task_name,
            cron_expression: formData.cron_expression,
            config,
            is_enabled: formData.is_enabled
          }
          emit('submit', scheduledSubmitData)
        } else {
          // 即时任务
          if (formData.task_type === 'crawl_task') {
            config = {} as CrawlTaskConfig
            if (crawlConfig.keywords.trim()) {
              config.keywords = crawlConfig.keywords.split(',').map((k: string) => k.trim()).filter(Boolean)
            }
            if (crawlConfig.dateRange && crawlConfig.dateRange.length === 2) {
              config.date_range = {
                start: crawlConfig.dateRange[0],
                end: crawlConfig.dateRange[1],
              }
            }
            if (crawlConfig.limitPages) {
              config.limit_pages = crawlConfig.limitPages
            }
            if (crawlConfig.selectedDataSources.length > 0) {
              const filteredSources = availableDataSources.value
                .filter((source: DataSourceConfig) => crawlConfig.selectedDataSources.includes(source.name))

              console.log('即时任务数据源过滤结果:', {
                selected: crawlConfig.selectedDataSources,
                available: availableDataSources.value.map(s => s.name),
                filtered: filteredSources.map(s => s.name)
              })

              config.data_sources = filteredSources
                .map((source: DataSourceConfig) => ({
                  ...source,
                  enabled: true
                }))

              console.log('即时任务最终数据源配置:', config.data_sources)
            } else {
              console.warn('警告: 即时任务没有选择数据源')
            }
          } else {
            config = {
              backup_type: backupConfig.backup_type,
              retention_policy: backupConfig.retention_policy,
              compression: backupConfig.compression,
              include_data: backupConfig.include_data
            } as BackupTaskConfig
          }
        }

        const taskSubmitData: TaskFormData = {
          task_type: formData.task_type,
          task_name: formData.task_name,
          config,
          autoStart: formData.autoStart
        }
        emit('submit', taskSubmitData)
      } catch (error) {
        console.error('提交失败:', error)
        ElMessage.error('提交失败，请重试')
      } finally {
        loading.value = false
      }
    }
  })
}

// 监听任务类型变化
watch(() => formData.task_type, handleTaskTypeChange)
watch(() => formData.scheduled_task_type, handleScheduledTaskTypeChange)

// 监听数据源选择变化，用于调试
watch(() => crawlConfig.selectedDataSources, (newVal) => {
  console.log('数据源选择变化:', newVal)
}, { deep: true })

onMounted(() => {
  // 组件挂载时的初始化逻辑
})
</script>

<style lang="scss" scoped>
.task-form {
  .cron-input-group {
    display: flex;
    gap: 10px;

    .cron-input {
      flex: 1;
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

    .next-run-time {
      margin: 5px 0 0 0;
      color: #67c23a;
    }
  }

  .help-text {
    margin-left: 10px;
    font-size: 12px;
    color: #909399;
  }

  // 修复选择框过小的问题
  :deep(.el-select) {
    min-width: 200px;

    // 确保下拉选项能正常显示
    .el-select__tags {
      max-width: 160px;
    }
  }

  // 任务类型选择框
  :deep(.el-form-item[prop="task_type"] .el-select),
  :deep(.el-form-item[prop="scheduled_task_type"] .el-select) {
    min-width: 220px;
  }

  // 数据源选择框
  :deep(.el-form-item[prop="crawlConfig.selectedDataSources"]) {
    :deep(.el-checkbox-group) {
      max-height: 200px;
      overflow-y: auto;

      .el-checkbox {
        display: block;
        margin-bottom: 8px;
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .task-form {
    .cron-input-group {
      flex-direction: column;

      .cron-input {
        margin-bottom: 10px;
      }
    }
  }
}
</style>
