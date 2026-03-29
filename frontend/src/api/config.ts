import apiClient from './client'
import type {
  FeatureFlagsResponse,
  S3ConfigResponse,
  S3ConfigUpdate,
  EmailConfigResponse,
  EmailConfigUpdate,
  TestResponse,
} from '../types/config'

export const configApi = {
  // 获取功能开关
  getFeatureFlags(): Promise<FeatureFlagsResponse> {
    return apiClient.get('/api/config/feature-flags').then((res) => res.data)
  },

  // 更新功能开关
  updateFeatureFlag(flagName: string, enabled: boolean): Promise<FeatureFlagsResponse> {
    // 后端使用Body(..., embed=True)，需要发送 {"enabled": true} 格式
    return apiClient
      .put(`/api/config/feature-flags/${flagName}`, { enabled })
      .then((res) => res.data)
  },

  // 获取S3配置
  getS3Config(): Promise<S3ConfigResponse> {
    return apiClient.get('/api/config/s3').then((res) => res.data)
  },

  // 更新S3配置
  updateS3Config(data: S3ConfigUpdate): Promise<S3ConfigResponse> {
    return apiClient.put('/api/config/s3', data).then((res) => res.data)
  },

  // 测试S3配置
  testS3Config(data?: Partial<S3ConfigUpdate>): Promise<TestResponse> {
    return apiClient.post('/api/config/s3/test', data || {}).then((res) => res.data)
  },

  // 获取邮件配置
  getEmailConfig(): Promise<EmailConfigResponse> {
    return apiClient.get('/api/config/email').then((res) => res.data)
  },

  // 更新邮件配置
  updateEmailConfig(data: EmailConfigUpdate): Promise<EmailConfigResponse> {
    return apiClient.put('/api/config/email', data).then((res) => res.data)
  },

  // 测试邮件配置（测试连接）
  testEmailConfig(data?: Partial<EmailConfigUpdate>): Promise<TestResponse> {
    return apiClient.post('/api/config/email/test', data || {}).then((res) => res.data)
  },

  // 发送测试邮件
  sendTestEmail(toAddress: string, config?: Partial<EmailConfigUpdate>): Promise<TestResponse> {
    return apiClient.post('/api/config/email/send-test', {
      to_address: toAddress,
      config: config || undefined,
    }).then((res) => res.data)
  },

  // 获取数据源列表
  getDataSources(): Promise<{ data_sources: Array<{
    name: string
    base_url?: string
    search_api?: string
    ajax_api?: string
    search_portal_url?: string
    channel_id?: string
    enabled: boolean
    // GD数据源特有字段
    type?: string
    api_base_url?: string
    law_rule_types?: number[]
  }> }> {
    return apiClient.get('/api/config/data-sources').then((res) => res.data)
  },

  // 获取爬虫配置
  getCrawlerConfig(): Promise<{ 
    request_delay: number
    use_proxy: boolean
    kuaidaili_secret_id?: string
    kuaidaili_secret_key?: string
    kuaidaili_api_key?: string
  }> {
    return apiClient.get('/api/config/crawler').then((res) => res.data)
  },

  // 更新爬虫配置
  updateCrawlerConfig(data: { 
    request_delay?: number
    use_proxy?: boolean
    kuaidaili_secret_id?: string
    kuaidaili_secret_key?: string
    kuaidaili_api_key?: string
  }): Promise<{ 
    request_delay: number
    use_proxy: boolean
    kuaidaili_secret_id?: string
    kuaidaili_secret_key?: string
    kuaidaili_api_key?: string
  }> {
    return apiClient.put('/api/config/crawler', data).then((res) => res.data)
  },

  // 测试快代理连接
  testKDLConnection(secretId: string, secretKey: string): Promise<TestResponse> {
    return apiClient.post('/api/config/crawler/test-kdl', {
      secret_id: secretId,
      secret_key: secretKey,
    }).then((res) => res.data)
  },

  // 检查邮件服务是否可用（公开端点，不需要认证）
  checkEmailAvailable(): Promise<{ available: boolean; enabled: boolean; configured: boolean }> {
    return apiClient.get('/api/config/email/available').then((res) => res.data)
  },
}

