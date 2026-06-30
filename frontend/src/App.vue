<template>
  <div id="app-container">
    <!-- 数据库警告横幅 -->
    <div v-if="dbWarning" class="db-warning-bar">
      ⚠️ {{ dbWarning }}
    </div>

    <!-- 顶部菜单栏（始终可见，全部展开） -->
    <header class="app-header">
      <div class="header-left">
        <span class="nav-brand">🌙 睡眠质量分析系统</span>
        <nav class="nav-links">
          <!-- 公开导航（所有人可见） -->
          <router-link to="/home" class="nav-link" active-class="nav-link--active">🏠 首页</router-link>
          <router-link to="/vis" class="nav-link" active-class="nav-link--active">📊 可视化分析</router-link>

          <!-- 登录后导航 -->
          <template v-if="isLoggedIn">
            <router-link to="/user/data" class="nav-link" active-class="nav-link--active">📁 数据管理</router-link>
            <router-link to="/user/predict" class="nav-link" active-class="nav-link--active">🔮 睡眠预测</router-link>
            <router-link to="/user/center" class="nav-link" active-class="nav-link--active">👤 个人中心</router-link>
          </template>

          <!-- 管理员导航 -->
          <template v-if="isAdmin">
            <router-link to="/admin/home" class="nav-link nav-link--admin" active-class="nav-link--active">🛡️ 管理首页</router-link>
            <router-link to="/admin/users" class="nav-link nav-link--admin" active-class="nav-link--active">👥 用户管理</router-link>
            <router-link to="/admin/vis" class="nav-link nav-link--admin" active-class="nav-link--active">📈 群体分析</router-link>
          </template>
        </nav>
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
    </header>

    <!-- 主内容区 -->
    <el-main class="app-main">
      <router-view @login-success="onLoginSuccess" :key="loginStamp" />
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
const loginStamp = ref(0)
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
  loginStamp.value++
  router.push('/home')
}

async function onLoginSuccess() {
  await checkLogin()
  loginStamp.value++
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

/* ====== 顶部导航栏（始终可见，全展开不折叠） ====== */
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: nowrap;
  background: linear-gradient(135deg, #1a2a3a 0%, #0f1923 100%);
  border-bottom: 1px solid #2a3a4a;
  padding: 8px 20px; min-height: 56px;
}
.header-left {
  display: flex; align-items: center; gap: 12px;
  flex-wrap: wrap; flex: 1 1 auto; min-width: 0;
}
.header-right {
  display: flex; align-items: center; gap: 12px;
  flex-shrink: 0; white-space: nowrap;
  margin-left: 16px;
  padding-left: 16px;
  border-left: 1px solid #2a3a4a;
}
.nav-brand {
  color: #ffd04b; font-weight: bold; font-size: 16px; white-space: nowrap;
  margin-right: 4px;
}

/* ====== 导航链接行（永远平铺不解锁） ====== */
.nav-links {
  display: flex; align-items: center; flex-wrap: wrap; gap: 4px;
}
.nav-link {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px; font-weight: 500;
  color: #b0b8c4;
  text-decoration: none;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}
.nav-link:hover {
  color: #ffd04b;
  background: rgba(255,208,75,0.08);
  border-bottom-color: rgba(255,208,75,0.3);
}
.nav-link--active {
  color: #ffd04b !important;
  background: rgba(255,208,75,0.12);
  border-bottom-color: #ffd04b;
  font-weight: 600;
}
.nav-link--admin {
  color: #e07080;
}
.nav-link--admin:hover,
.nav-link--admin.nav-link--active {
  color: #ff8090 !important;
  border-bottom-color: #ff8090;
  background: rgba(255,100,120,0.1);
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
