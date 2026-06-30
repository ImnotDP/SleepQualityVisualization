import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true,
})

// ========== 系统状态 ==========
export function getSystemStatus() {
  return api.get('/status')
}

// ========== 认证 ==========
export function register(username, password, confirm_password) {
  return api.post('/auth/register', { username, password, confirm_password })
}
export function login(username, password) {
  return api.post('/auth/login', { username, password })
}
export function logout() {
  return api.post('/auth/logout')
}
export function getCurrentUser() {
  return api.get('/auth/me')
}
export function checkAdmin() {
  return api.get('/auth/check_admin')
}

// ========== 数据管理 ==========
export function uploadCsv(file) {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/data/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}
export function uploadZip(file) {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/data/upload_zip', fd, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 })
}
export function uploadMulti(files) {
  const fd = new FormData()
  files.forEach(f => fd.append('files', f))
  return api.post('/data/upload_multi', fd, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 })
}
export function processAll() {
  return api.post('/data/process_all')
}
export function getRecords(page = 1, pageSize = 30) {
  return api.get('/data/records', { params: { page, page_size: pageSize } })
}
export function getRecordDetail(id) {
  return api.get(`/data/records/${id}`)
}
export function deleteRecord(id) {
  return api.delete(`/data/records/${id}`)
}
export function runPreprocess() {
  return api.post('/data/preprocess')
}
export function getPersonalStats() {
  return api.get('/data/stats')
}
export function getPublicSummary() {
  return api.get('/data/public_summary')
}

// ========== 可视化 ==========
export function getScatterData() {
  return api.get('/vis/scatter')
}
export function getHistogramData() {
  return api.get('/vis/histogram')
}
export function getCorrelationData() {
  return api.get('/vis/correlation')
}
export function getStagePieData() {
  return api.get('/vis/stage_pie')
}
export function getTrendData() {
  return api.get('/vis/trend')
}
export function getScatterMatrixData() {
  return api.get('/vis/scatter_matrix')
}
export function getSleepStructure() {
  return api.get('/vis/sleep_structure')
}
export function getEnvironmentData() {
  return api.get('/vis/environment')
}
export function getEnvironmentVsQuality() {
  return api.get('/vis/environment_vs_quality')
}

// ========== 公开可视化（无需登录） ==========
export function getPublicTrend() {
  return api.get('/vis/public/trend')
}
export function getPublicStagePie() {
  return api.get('/vis/public/stage_pie')
}
export function getPublicCorrelation() {
  return api.get('/vis/public/correlation')
}
export function getPublicScatter() {
  return api.get('/vis/public/scatter')
}
export function getPublicSleepStructure() {
  return api.get('/vis/public/sleep_structure')
}
export function getPublicModelComparison() {
  return api.get('/vis/public/model_comparison')
}

// ========== 预测 ==========
export function predictScore(params) {
  return api.post('/predict/score', params)
}
export function quickScore(params) {
  return api.post('/predict/quick_score', params)
}
export function getReports(page = 1, pageSize = 20) {
  return api.get('/predict/reports', { params: { page, page_size: pageSize } })
}
export function getReportDetail(id) {
  return api.get(`/predict/reports/${id}`)
}
export function getFeatureAnalysis() {
  return api.get('/predict/feature_analysis')
}
export function getAutoAnalysis() {
  return api.post('/predict/auto_analysis')
}

// ========== 算法模型 ==========
export function getAlgorithmComparison() {
  return api.get('/predict/feature_analysis')
}

// ========== 管理员 ==========
export function getAdminDashboard() {
  return api.get('/admin/dashboard')
}
export function getAdminUsers(page = 1, pageSize = 50) {
  return api.get('/admin/users', { params: { page, page_size: pageSize } })
}
export function deleteAdminUser(id) {
  return api.delete(`/admin/users/${id}`)
}
export function getAdminAllRecords(page = 1, pageSize = 30, userId = null) {
  return api.get('/admin/all_records', { params: { page, page_size: pageSize, user_id: userId } })
}
export function deleteAdminRecord(id) {
  return api.delete(`/admin/delete_record/${id}`)
}
export function getGroupQualityDist() {
  return api.get('/admin/group_quality_distribution')
}
export function getGroupSleepStructure() {
  return api.get('/admin/group_sleep_structure')
}
export function getGroupInfluenceRanking() {
  return api.get('/admin/group_influence_ranking')
}
export function getGlobalCorrelation() {
  return api.get('/vis/admin/global_correlation')
}
export function getGlobalDistribution() {
  return api.get('/vis/admin/global_distribution')
}

export default api
