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
export function register(username, password) {
  return api.post('/auth/register', { username, password })
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

// ========== 预测 ==========
export function predictScore(params) {
  return api.post('/predict/score', params)
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
