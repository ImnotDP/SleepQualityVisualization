<template>
  <div class="auth-page">
    <el-card class="auth-card card-dark">
      <template #header><h2 style="text-align:center">📝 注册</h2></template>
      <el-form :model="form" label-width="0">
        <el-form-item><el-input v-model="form.username" placeholder="用户名（至少3位）" prefix-icon="User" /></el-form-item>
        <el-form-item><el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" show-password /></el-form-item>
        <el-form-item><el-input v-model="form.confirm_password" type="password" placeholder="确认密码" prefix-icon="Lock" show-password /></el-form-item>
        <el-form-item>
          <el-button type="primary" @click="doRegister" :loading="loading" style="width:100%">注 册</el-button>
        </el-form-item>
      </el-form>
      <div style="text-align:center">
        <el-button text type="primary" @click="$router.push('/login')">已有账号？返回登录</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../api/sleep'
import { ElMessage } from 'element-plus'

const router = useRouter()
const form = reactive({ username: '', password: '', confirm_password: '' })
const loading = ref(false)

async function doRegister() {
  if (!form.username || !form.password) { ElMessage.warning('请填写所有字段'); return }
  if (form.password !== form.confirm_password) { ElMessage.warning('两次密码不一致'); return }
  loading.value = true
  try {
    await register(form.username, form.password, form.confirm_password)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '注册失败')
  } finally { loading.value = false }
}
</script>

<style scoped>
.auth-page { display:flex; justify-content:center; align-items:center; min-height:100vh; background:#0f1923; }
.auth-card { width:400px; }
</style>
