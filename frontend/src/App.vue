<!--
==============================================================================
MNR Law Crawler Online - Vue应用主入口
==============================================================================

项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
作者: ViVi141
许可证: MIT License

描述: Vue 3应用的主入口文件，负责路由渲染和全局状态管理

==============================================================================
-->
<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  // 尝试从localStorage恢复登录状态
  const token = localStorage.getItem('token')
  if (token) {
    authStore.setToken(token)
    // 验证token是否有效
    authStore.getCurrentUser().catch(() => {
      // token无效则清除
      authStore.logout()
    })
  }
})
</script>

<style lang="scss">
* {
  box-sizing: border-box;
}

#app {
  width: 100%;
  height: 100vh;
  overflow: hidden;
  position: relative;
}
</style>


