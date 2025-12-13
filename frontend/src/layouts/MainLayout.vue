<template>
  <el-container class="main-layout">
    <el-header class="header">
      <div class="header-left">
        <h1 class="logo">MNR法规爬虫系统</h1>
      </div>
      <div class="header-right">
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            <span>{{ authStore.user?.username || '用户' }}</span>
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-container>
      <el-aside width="200px" class="sidebar">
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/policies">
            <el-icon><Document /></el-icon>
            <span>政策列表</span>
          </el-menu-item>
          <el-menu-item index="/tasks">
            <el-icon><List /></el-icon>
            <span>任务管理</span>
          </el-menu-item>
          <el-menu-item index="/scheduled-tasks">
            <el-icon><Timer /></el-icon>
            <span>定时任务</span>
          </el-menu-item>
          <el-menu-item index="/backups">
            <el-icon><Box /></el-icon>
            <span>备份管理</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
          <el-menu-item index="/about">
            <el-icon><InfoFilled /></el-icon>
            <span>关于项目</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  User,
  ArrowDown,
  Document,
  List,
  Timer,
  Box,
  Setting,
  InfoFilled,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
      authStore.logout()
      router.push('/login')
      ElMessage.success('已退出登录')
    } catch {
      // 用户取消
    }
  }
}
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: #409eff;
  color: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.12);

  .header-left {
    .logo {
      font-size: 20px;
      font-weight: 500;
      margin: 0;
    }
  }

  .header-right {
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 5px 10px;
      border-radius: 4px;
      transition: background-color 0.3s;

      &:hover {
        background-color: rgba(255, 255, 255, 0.1);
      }
    }
  }
}

.sidebar {
  background-color: #f5f5f5;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;

  .sidebar-menu {
    border-right: none;
    background-color: transparent;
  }
}

.main-content {
  background-color: #f0f2f5;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
  min-height: 0; // 允许flex子元素收缩
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  
  // 路由视图容器可以滚动
  & > :deep(> *) {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 20px;
    
    &::-webkit-scrollbar {
      width: 8px;
    }
  }
  
  &::-webkit-scrollbar-track {
    background: #f1f1f1;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 4px;
    
    &:hover {
      background: #555;
    }
  }
}

// 响应式布局
@media (max-width: 768px) {
  .sidebar {
    width: 64px !important;
    
    .sidebar-menu {
      span {
        display: none;
      }
    }
  }
  
  .header {
    .logo {
      font-size: 16px !important;
    }
  }
}

.dark {
  .sidebar {
    background-color: #1f1f1f;
    border-right-color: #4a4a4a;
  }

  .main-content {
    background-color: #141414;
  }
}
</style>

