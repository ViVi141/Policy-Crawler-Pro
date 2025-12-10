import axios, { type AxiosInstance, type AxiosResponse, type AxiosError } from 'axios'

// 在生产环境（Docker）中使用相对路径，通过 Nginx 代理访问后端
// 在开发环境中使用环境变量或默认值
// 如果设置了 VITE_API_BASE_URL，优先使用；否则在生产环境使用空字符串（相对路径），开发环境使用 localhost
// 注意：前端代码中已使用 /api/xxx 路径，所以 baseURL 应为空字符串，nginx 会将 /api 代理到后端
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.PROD ? '' : 'http://localhost:8000')

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error: AxiosError) => {
    // 401错误，清除token并跳转到登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // 使用router跳转，避免硬刷新
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient


