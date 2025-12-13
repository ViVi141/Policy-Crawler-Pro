// ==============================================================================
// MNR Law Crawler Online - Vue应用主入口
// ==============================================================================
//
// 项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
// 项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
// 作者: ViVi141
// 许可证: MIT License
//
// 描述: Vue 3应用的主入口文件，负责应用初始化、插件配置和挂载
//
// ==============================================================================

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
// @ts-expect-error - element-plus locale type issue
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './styles/main.scss'

const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue) as [string, unknown][]) {
  app.component(key, component as Parameters<typeof app.component>[1])
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})

app.mount('#app')


