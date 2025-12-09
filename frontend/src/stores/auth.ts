import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'
import type { LoginRequest, UserInfo } from '../types/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<UserInfo | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUser(userInfo: UserInfo) {
    user.value = userInfo
  }

  async function login(credentials: LoginRequest) {
    const response = await authApi.login(credentials)
    setToken(response.access_token)
    await getCurrentUser()
    return response
  }

  async function getCurrentUser() {
    try {
      const userInfo = await authApi.getCurrentUser()
      setUser(userInfo)
      return userInfo
    } catch (error: unknown) {
      logout()
      throw error
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    isAuthenticated,
    setToken,
    setUser,
    login,
    getCurrentUser,
    logout,
  }
})


