<template>
  <div class="auth-page">
    <el-card class="auth-card card-dark">
      <template #header><h2 style="text-align:center">🌙 登录</h2></template>
      <el-form :model="form" label-width="0" @keyup.enter="doLogin">
        <el-form-item><el-input v-model="form.username" placeholder="用户名" prefix-icon="User" /></el-form-item>
        <el-form-item><el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" show-password /></el-form-item>
        <el-form-item>
          <el-button type="primary" @click="doLogin" :loading="loading" style="width:100%">登 录</el-button>
        </el-form-item>
      </el-form>
      <div style="text-align:center">
        <el-button text type="primary" @click="$router.push('/register')">还没有账号？立即注册</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api/sleep'
import { ElMessage } from 'element-plus'

const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const emit = defineEmits(['login-success'])

async function doLogin() {
  if (!form.username || !form.password) { ElMessage.warning('请输入用户名和密码'); return }
  loading.value = true
  try {
    await login(form.username, form.password)
    ElMessage.success('登录成功')
    emit('login-success')
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '登录失败')
  } finally { loading.value = false }
}
</script>

<style scoped>
.auth-page { display:flex; justify-content:center; align-items:center; min-height:100vh; background:#0f1923; }
.auth-card { width:400px; }
</style>
