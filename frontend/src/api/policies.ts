import apiClient from './client'
import type { Policy, PolicyListResponse, PolicySearchParams } from '../types/policy'

export const policiesApi = {
  // 获取政策列表
  getPolicies(params?: PolicySearchParams): Promise<PolicyListResponse> {
    // 转换参数：page -> skip, page_size -> limit
    const queryParams: Record<string, unknown> = {}
    
    if (params) {
      // 分页参数转换
      if (params.page !== undefined && params.page_size !== undefined) {
        queryParams.skip = (params.page - 1) * params.page_size
        queryParams.limit = params.page_size
      }
      
      // 筛选参数：只传递非空值（过滤空字符串）
      if (params.keyword && params.keyword.trim()) {
        queryParams.keyword = params.keyword.trim()
      }
      if (params.category && params.category.trim()) {
        queryParams.category = params.category.trim()
      }
      if (params.level && params.level.trim()) {
        queryParams.level = params.level.trim()
      }
      if (params.publisher && params.publisher.trim()) {
        queryParams.publisher = params.publisher.trim()
      }
      if (params.start_date && params.start_date.trim()) {
        queryParams.start_date = params.start_date.trim()
      }
      if (params.end_date && params.end_date.trim()) {
        queryParams.end_date = params.end_date.trim()
      }
      if (params.source_name && params.source_name.trim()) {
        queryParams.source_name = params.source_name.trim()
      }
      if (params.task_id !== undefined && params.task_id !== null) {
        queryParams.task_id = params.task_id
      }
    }
    
    return apiClient.get('/api/policies/', { params: queryParams }).then((res) => {
      const data = res.data
      // 转换响应格式：后端返回 skip/limit，前端期望 page/page_size
      // 字段映射转换：将后端字段名转换为前端字段名
      const items = (data.items || []).map((item: Partial<Policy> & Record<string, string | number | boolean | null | undefined>) => ({
        ...item,
        // 基本字段映射
        publishDate: item.publish_date || item.pub_date || null, // 发布日期
        effectiveDate: item.effective_date || null, // 生效日期
        docNumber: item.doc_number || null, // 文号
        lawLevel: item.level || item.law_type || null, // 效力级别
        sourceName: item.source_name || null, // 数据源名称
        sourceUrl: item.source_url || item.source || null, // 数据源URL
        createdAt: item.created_at || null, // 创建时间
        updatedAt: item.updated_at || null, // 更新时间
        // 保留原始字段以兼容性
        publish_date: item.publish_date || item.pub_date || null,
        law_type: item.level || item.law_type || null,
      }))
      
      if (data.skip !== undefined && data.limit !== undefined) {
        return {
          ...data,
          items,
          page: Math.floor(data.skip / data.limit) + 1,
          page_size: data.limit,
          total_pages: Math.ceil(data.total / data.limit)
        }
      }
      return { ...data, items }
    })
  },

  // 获取政策详情
  getPolicyById(id: number): Promise<Policy> {
    return apiClient.get(`/api/policies/${id}`).then((res) => {
      const item = res.data
      // 应用与列表页相同的字段映射转换
      return {
        ...item,
        // 基本字段映射
        publishDate: item.publish_date || item.pub_date || null, // 发布日期
        effectiveDate: item.effective_date || null, // 生效日期
        docNumber: item.doc_number || null, // 文号
        lawLevel: item.level || item.law_type || null, // 效力级别
        sourceName: item.source_name || null, // 数据源名称
        sourceUrl: item.source_url || item.source || null, // 数据源URL
        createdAt: item.created_at || null, // 创建时间
        updatedAt: item.updated_at || null, // 更新时间
        // 保留原始字段以兼容性
        publish_date: item.publish_date || item.pub_date || null,
        law_type: item.level || item.law_type || null,
      }
    })
  },

  // 搜索政策
  searchPolicies(params: PolicySearchParams): Promise<PolicyListResponse> {
    return apiClient.get('/api/policies/search', { params }).then((res) => {
      const data = res.data
      // 转换响应格式并应用字段映射
      const items = (data.items || []).map((item: Partial<Policy> & Record<string, string | number | boolean | null | undefined>) => ({
        ...item,
        // 基本字段映射
        publishDate: item.publish_date || item.pub_date || null, // 发布日期
        effectiveDate: item.effective_date || null, // 生效日期
        docNumber: item.doc_number || null, // 文号
        lawLevel: item.level || item.law_type || null, // 效力级别
        sourceName: item.source_name || null, // 数据源名称
        sourceUrl: item.source_url || item.source || null, // 数据源URL
        createdAt: item.created_at || null, // 创建时间
        updatedAt: item.updated_at || null, // 更新时间
        // 保留原始字段以兼容性
        publish_date: item.publish_date || item.pub_date || null,
        law_type: item.level || item.law_type || null,
      }))

      return { ...data, items }
    })
  },

  // 下载政策文件
  downloadPolicy(id: number, fileType: string = 'markdown'): Promise<Blob> {
    return apiClient
      .get(`/api/policies/${id}/file/${fileType}`, {
        responseType: 'blob',
      })
      .then((res) => res.data)
  },

  // 下载附件文件
  downloadAttachment(id: number, attachmentId: number): Promise<Blob> {
    return apiClient
      .get(`/api/policies/${id}/attachments/${attachmentId}/download`, {
        responseType: 'blob',
      })
      .then((res) => res.data)
  },

  // 获取所有数据源名称列表
  getSourceNames(): Promise<string[]> {
    return apiClient.get('/api/policies/meta/source-names').then((res) => res.data)
  },

  // 获取分类列表（可选按数据源筛选）
  getCategories(sourceName?: string): Promise<string[]> {
    const params: Record<string, unknown> = {}
    if (sourceName && sourceName.trim()) {
      params.source_name = sourceName.trim()
    }
    return apiClient.get('/api/policies/meta/categories', { params }).then((res) => res.data)
  },
}

