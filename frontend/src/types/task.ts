import type { TaskConfig, TaskResult } from './common'

export interface Task {
  id: number
  task_type: string
  task_name: string
  status: string
  progress: number
  config_json?: TaskConfig
  result_json?: TaskResult
  error_message?: string
  progress_message?: string  // 实时进度消息
  progress_data?: DetailedCrawlProgress  // 详细进度数据
  started_at?: string
  start_time?: string
  completed_at?: string
  end_time?: string
  created_at: string
  updated_at?: string
  policy_count?: number
  success_count?: number
  failed_count?: number
}

export interface TaskCreateRequest {
  task_type: string
  task_name: string
  config?: TaskConfig
}

export interface TaskListResponse {
  items: Task[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 爬取阶段信息
export interface CrawlStage {
  name: string
  description: string
  total_count: number
  completed_count: number
  failed_count: number
  progress_percentage: number
  success_rate: number
  status: string
  message: string
  start_time?: string
  end_time?: string
}

// 详细的爬取进度信息
export interface DetailedCrawlProgress {
  // 总体进度
  total_count: number
  completed_count: number
  failed_count: number
  success_rate: number
  progress_percentage: number

  // 当前处理信息
  current_policy_id: string
  current_policy_title: string
  current_stage: string

  // 时间信息
  start_time?: string
  end_time?: string
  elapsed_time?: number

  // 历史记录
  completed_policies: string[]
  failed_policies: Array<{id: string, title: string, reason: string}>

  // 多阶段进度
  stages: Record<string, CrawlStage>
  current_stage_progress: number
}

// SSE 进度推送消息类型
export interface ProgressMessage {
  type: 'task_update' | 'progress_update' | 'heartbeat'
  task_id?: number
  status?: string
  message?: string
  progress_message?: string
  progress_data?: DetailedCrawlProgress
  start_time?: string
  updated_at?: string
  timestamp?: string
}

