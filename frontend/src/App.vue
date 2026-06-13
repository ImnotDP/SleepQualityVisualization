<template>
  <div id="app-container">
    <!-- 数据库警告横幅 -->
    <div v-if="dbWarning" class="db-warning-bar">
      ⚠️ {{ dbWarning }}
    </div>

    <!-- 顶部菜单栏（始终可见） -->
    <el-header class="app-header">
      <div class="header-left">
        <span class="nav-brand">🌙 睡眠质量分析系统</span>
        <el-menu
          mode="horizontal"
          :default-active="activeRoute"
          router
          background-color="transparent"
          text-color="#e0e0e0"
          active-text-color="#ffd04b"
          class="nav-menu"
        >
          <!-- 公开菜单（所有人可见） -->
          <el-menu-item index="/home">🏠 首页</el-menu-item>
          <el-menu-item index="/vis">📊 可视化分析</el-menu-item>

          <!-- 登录后菜单 -->
          <template v-if="isLoggedIn">
            <el-menu-item index="/user/data">📁 数据管理</el-menu-item>
            <el-menu-item index="/user/predict">🔮 睡眠预测</el-menu-item>
            <el-menu-item index="/user/center">👤 个人中心</el-menu-item>
          </template>

          <!-- 管理员菜单 -->
          <template v-if="isAdmin">
            <el-menu-item index="/admin/home">🛡️ 管理首页</el-menu-item>
            <el-menu-item index="/admin/users">👥 用户管理</el-menu-item>
            <el-menu-item index="/admin/vis">📈 群体分析</el-menu-item>
          </template>
        </el-menu>
      </div>
      <div class="header-right">
        <!-- 未登录 -->
        <template v-if="!isLoggedIn">
          <el-button type="primary" size="small" @click="$router.push('/login')">登 录</el-button>
          <el-button text size="small" style="color:#ccc" @click="$router.push('/register')">注 册</el-button>
        </template>
        <!-- 已登录 -->
        <template v-else>
          <span class="username">{{ currentUser?.username }}</span>
          <el-tag v-if="isAdmin" type="danger" size="small">管理员</el-tag>
          <el-tag v-else type="success" size="small">用户</el-tag>
          <el-button type="danger" text size="small" @click="doLogout">退出</el-button>
        </template>
      </div>
    </el-header>

    <!-- 主内容区 -->
    <el-main class="app-main">
      <router-view @login-success="onLoginSuccess" />
    </el-main>
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
  router.push('/home')
}

async function onLoginSuccess() {
  await checkLogin()
  const u = currentUser.value
  router.push(u?.role === 'admin' ? '/admin/home' : '/home')
}

checkLogin()
onMounted(checkDbStatus)
</script>

<style>
/* ====== 全局样式 ====== */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0f1923; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
#app-container { min-height: 100vh; }

/* 数据库警告 */
.db-warning-bar {
  background: #e6a23c; color: #000; text-align: center; padding: 6px; font-size: 13px;
}

/* ====== 顶部菜单栏（始终可见） ====== */
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  background: linear-gradient(135deg, #1a2a3a 0%, #0f1923 100%);
  border-bottom: 1px solid #2a3a4a;
  padding: 0 20px; height: 56px;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.header-right { display: flex; align-items: center; gap: 12px; white-space: nowrap; }
.nav-brand {
  color: #ffd04b; font-weight: bold; font-size: 16px; white-space: nowrap;
  margin-right: 10px;
}
.nav-menu {
  background: transparent !important; border-bottom: none !important;
}
.nav-menu .el-menu-item {
  color: #ccc !important; border-bottom: 2px solid transparent !important;
  height: 56px; line-height: 56px;
}
.nav-menu .el-menu-item:hover,
.nav-menu .el-menu-item.is-active {
  color: #ffd04b !important; border-bottom-color: #ffd04b !important;
  background: transparent !important;
}
.username { color: #ccc; font-size: 14px; }

/* ====== 主内容 ====== */
.app-main {
  min-height: 100vh; padding: 20px;
  max-width: 1400px; margin: 0 auto;
}

/* 公共卡片样式 */
.card-dark { background: #1a2a3a; border: 1px solid #2a3a4a; color: #e0e0e0; margin-bottom: 20px; }
.card-dark .el-card__header { border-bottom: 1px solid #2a3a4a; color: #e0e0e0; }
.stat-value { font-size: 2rem; font-weight: 700; color: #ffd04b; }
.stat-label { font-size: 0.85rem; color: #8899aa; }
</style>
