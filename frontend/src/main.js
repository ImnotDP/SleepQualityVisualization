import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'

// 页面组件
import LoginPage from './components/LoginPage.vue'
import RegisterPage from './components/RegisterPage.vue'
import UserHome from './components/UserHome.vue'
import UserCenter from './components/UserCenter.vue'
import DataManage from './components/DataManage.vue'
import VisualizePage from './components/VisualizePage.vue'
import PredictPage from './components/PredictPage.vue'
import AdminHome from './components/AdminHome.vue'
import AdminUsers from './components/AdminUsers.vue'
import AdminVis from './components/AdminVis.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: LoginPage, meta: { guest: true } },
  { path: '/register', name: 'register', component: RegisterPage, meta: { guest: true } },
  { path: '/user/home', name: 'userHome', component: UserHome, meta: { requiresAuth: true } },
  { path: '/user/center', name: 'userCenter', component: UserCenter, meta: { requiresAuth: true } },
  { path: '/user/data', name: 'dataManage', component: DataManage, meta: { requiresAuth: true } },
  { path: '/user/vis', name: 'visualize', component: VisualizePage, meta: { requiresAuth: true } },
  { path: '/user/predict', name: 'predict', component: PredictPage, meta: { requiresAuth: true } },
  { path: '/admin/home', name: 'adminHome', component: AdminHome, meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/users', name: 'adminUsers', component: AdminUsers, meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/vis', name: 'adminVis', component: AdminVis, meta: { requiresAuth: true, requiresAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const { getCurrentUser, checkAdmin } = await import('./api/sleep.js')
  try {
    const res = await getCurrentUser()
    const user = res.data.user
    const isLoggedIn = !!user
    const isAdmin = user && user.role === 'admin'

    if (to.meta.requiresAuth && !isLoggedIn) {
      return next('/login')
    }
    if (to.meta.requiresAdmin && !isAdmin) {
      return next('/user/home')
    }
    if (to.meta.guest && isLoggedIn) {
      return next(isAdmin ? '/admin/home' : '/user/home')
    }
    next()
  } catch {
    if (to.meta.requiresAuth) {
      return next('/login')
    }
    next()
  }
})

const app = createApp(App)
app.use(router)
app.use(ElementPlus)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
