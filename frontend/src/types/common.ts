import type { AxiosError } from 'axios'

// API错误响应类型
export interface ApiErrorResponse {
  detail?: string
  message?: string
  error?: string
}

// 扩展的Axios错误类型
export type ApiError = AxiosError<ApiErrorResponse>

// 数据源配置类型
export interface DataSourceConfig {
  name: string
  base_url?: string
  search_api?: string
  ajax_api?: string
  /** 检索前访问的门户页（如 g2018），用于 Cookie / Referer；列表接口仍为 was5/web/search */
  search_portal_url?: string
  channel_id?: string
  enabled: boolean
  // 广东省法规数据源特有字段
  type?: string
  api_base_url?: string
  law_rule_types?: number[]
}

// 任务配置类型
export interface CrawlTaskConfig {
  keywords?: string[]
  date_range?: {
    start?: string
    end?: string
  }
  start_date?: string
  end_date?: string
  limit_pages?: number
  data_sources?: DataSourceConfig[]  // 数据源配置，如果提供则使用指定的数据源
  auto_backup?: boolean  // 任务完成后是否自动备份（已废弃，使用backup配置）
  backup?: {
    enabled: boolean  // 是否启用自动备份
    strategy?: 'always' | 'on_success' | 'on_new_policies'  // 备份策略
    min_policies?: number  // 最小政策数量阈值（仅当策略为on_new_policies时有效）
  }
}

export interface BackupTaskConfig {
  backup_type?: 'full' | 'incremental'
}

export type TaskConfig = CrawlTaskConfig | BackupTaskConfig | Record<string, unknown>

// 任务结果类型
export interface TaskResult {
  success?: boolean
  message?: string
  policy_count?: number
  success_count?: number
  skipped_count?: number
  failed_count?: number
  error_count?: number
  [key: string]: unknown
}

// 附件类型
export interface Attachment {
  id: number
  filename: string
  file_type: string
  file_size: number
  file_path: string
  created_at: string
}

