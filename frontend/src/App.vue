<template>
  <div id="app-container">
    <!-- 数据库警告横幅 -->
    <div v-if="dbWarning" class="db-warning-bar">
      ⚠️ {{ dbWarning }}
    </div>
    <el-container v-if="isLoggedIn">
      <el-header class="app-header">
        <div class="header-left">
          <h1>🌙 睡眠质量分析系统</h1>
        </div>
        <div class="header-right">
          <el-menu
            mode="horizontal"
            :default-active="activeRoute"
            router
            background-color="transparent"
            text-color="#e0e0e0"
            active-text-color="#ffd04b"
          >
            <!-- 普通用户菜单 -->
            <template v-if="!isAdmin">
              <el-menu-item index="/user/home">🏠 个人首页</el-menu-item>
              <el-menu-item index="/user/center">👤 个人中心</el-menu-item>
              <el-menu-item index="/user/data">📁 数据管理</el-menu-item>
              <el-menu-item index="/user/vis">📊 可视化分析</el-menu-item>
              <el-menu-item index="/user/predict">🔮 睡眠预测</el-menu-item>
            </template>
            <!-- 管理员菜单 -->
            <template v-if="isAdmin">
              <el-menu-item index="/admin/home">🛡️ 管理首页</el-menu-item>
              <el-menu-item index="/admin/users">👥 用户管理</el-menu-item>
              <el-menu-item index="/admin/vis">📈 群体分析</el-menu-item>
              <el-menu-item index="/user/home">🏠 个人功能</el-menu-item>
              <el-menu-item index="/user/data">📁 数据管理</el-menu-item>
            </template>
          </el-menu>
          <div class="user-info">
            <span class="username">{{ currentUser?.username }}</span>
            <el-tag v-if="isAdmin" type="danger" size="small">管理员</el-tag>
            <el-tag v-else type="success" size="small">用户</el-tag>
            <el-button type="danger" text @click="doLogout">退出</el-button>
          </div>
        </div>
      </el-header>
      <el-main>
        <router-view @login-success="onLoginSuccess" />
      </el-main>
    </el-container>
    <!-- 未登录时直接显示登录/注册 -->
    <router-view v-else @login-success="onLoginSuccess" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { logout, getCurrentUser, getSystemStatus } from './api/sleep'

const route = useRoute()
const router = useRouter()
const currentUser = ref(null)
const dbWarning = ref('')
const isLoggedIn = computed(() => !!currentUser.value)
const isAdmin = computed(() => currentUser.value?.role === 'admin')
const activeRoute = computed(() => route.path)

async function checkDbStatus() {
  try {
    const res = await getSystemStatus()
    if (!res.data.mysql_available) {
      const err = res.data.mysql_error || '无法连接 MySQL 服务器'
      dbWarning.value = `MySQL 不可用，已回退 SQLite（${err}）。如需使用 MySQL，请检查服务是否启动。`
    }
  } catch { /* 后端未启动，忽略 */ }
}

async function checkLogin() {
  try {
    const res = await getCurrentUser()
    currentUser.value = res.data.user
  } catch {
    currentUser.value = null
  }
}

async function doLogout() {
  await logout()
  currentUser.value = null
  router.push('/login')
}

async function onLoginSuccess() {
  await checkLogin()
  const u = currentUser.value
  router.push(u?.role === 'admin' ? '/admin/home' : '/user/home')
}

checkLogin()
onMounted(checkDbStatus)
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
  background: #0f1923;
  color: #e0e0e0;
}
.db-warning-bar {
  background: #3a2a0a; color: #ffd04b; text-align: center;
  padding: 8px 16px; font-size: 0.9rem; border-bottom: 1px solid #5a4a1a;
}
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  background: linear-gradient(135deg, #1a2a3a 0%, #0d1b2a 100%);
  border-bottom: 1px solid #2a3a4a; padding: 0 24px; height: 64px;
}
.header-left h1 { font-size: 1.3rem; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 16px; }
.user-info { display: flex; align-items: center; gap: 8px; }
.username { color: #ffd04b; font-weight: 500; }
.el-menu--horizontal { border-bottom: none !important; }
.el-main { padding: 24px; min-height: calc(100vh - 64px); }

/* 公共卡片样式 */
.card-dark { background: #1a2a3a; border: 1px solid #2a3a4a; color: #e0e0e0; margin-bottom: 20px; }
.card-dark .el-card__header { border-bottom: 1px solid #2a3a4a; color: #e0e0e0; }
.stat-value { font-size: 2rem; font-weight: 700; color: #ffd04b; }
.stat-label { font-size: 0.85rem; color: #8899aa; }
</style>
