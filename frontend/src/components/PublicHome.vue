<template>
  <div class="page">
    <h2 style="margin-bottom:8px">🏠 睡眠质量可视化分析</h2>
    <el-alert v-if="!isLoggedIn" type="info" :closable="false" show-icon style="margin-bottom:16px">
      <template #title>
        当前为<strong>公开浏览模式</strong>（未登录）— 展示 DATA 文件夹的示例数据。
        如需<strong>上传个人手环数据</strong>获得专属分析，请点击右上角<strong>「注册」</strong>账号后登录。
      </template>
    </el-alert>
    <el-alert v-else type="success" :closable="false" show-icon style="margin-bottom:16px">
      <template #title>
        欢迎回来，<strong>{{ currentUser?.username }}</strong>！您已登录，可上传个人数据获得专属分析。
      </template>
    </el-alert>

    <!-- 统计卡片 -->
    <el-row :gutter="20" v-if="summary">
      <el-col :xs="24" :sm="12" :md="6" v-for="c in cards" :key="c.label">
        <el-card class="card-dark" shadow="hover">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value">{{ c.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图 -->
    <el-card class="card-dark" style="margin-top:20px" v-if="trendReady">
      <template #header>📈 睡眠质量趋势</template>
      <v-chart class="chart" :option="trendOption" autoresize />
    </el-card>

    <!-- 散点图 -->
    <el-card class="card-dark" style="margin-top:20px" v-if="scatterReady">
      <template #header>🎯 心率 vs 睡眠质量</template>
      <v-chart class="chart" :option="scatterHROption" autoresize />
    </el-card>

    <!-- 饼图 -->
    <el-card class="card-dark" style="margin-top:20px" v-if="pieReady">
      <template #header>🍰 睡眠阶段占比</template>
      <v-chart class="chart" :option="pieOption" autoresize />
    </el-card>

    <!-- 热力图 -->
    <el-card class="card-dark" style="margin-top:20px" v-if="corrReady">
      <template #header>🔥 特征相关性热力图</template>
      <v-chart class="chart" style="height:500px" :option="corrOption" autoresize />
    </el-card>

    <!-- 无数据提示 -->
    <el-empty v-if="!hasData && !loading" description="暂无数据，请先上传睡眠数据或检查 DATA 文件夹" />

    <!-- 操作提示 -->
    <el-card class="card-dark" style="margin-top:20px">
      <template #header>💡 想要上传自己的数据？</template>
      <p style="color:#889;margin-bottom:12px">上传您的睡眠数据（支持 CSV / ZIP 压缩包），获得个性化的睡眠分析报告和预测。</p>
      <el-button type="primary" @click="goUpload">📤 上传我的数据</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import { getPublicSummary, getPublicTrend, getPublicStagePie, getPublicCorrelation, getPublicScatter, getCurrentUser } from '../api/sleep'
import { ElMessage } from 'element-plus'
import { formatMinutes } from '../utils/format'

use([CanvasRenderer, LineChart, BarChart, PieChart, ScatterChart, HeatmapChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent])

const router = useRouter()
const loading = ref(true)
const hasData = ref(false)
const isLoggedIn = ref(false)
const currentUser = ref(null)
const summary = ref(null)
const trendReady = ref(false)
const scatterReady = ref(false)
const pieReady = ref(false)
const corrReady = ref(false)

const trendOption = ref({})
const scatterHROption = ref({})
const pieOption = ref({})
const corrOption = ref({})

const cards = computed(() => {
  if (!summary.value) return []
  const s = summary.value
  return [
    { label: '记录天数', value: s.total_records || 0 },
    { label: '平均质量分', value: s.avg_quality_score || '-' },
    { label: '平均睡眠', value: formatMinutes(s.avg_sleep_minutes) || '-' },
    { label: '平均效率', value: s.avg_efficiency ? (s.avg_efficiency * 100).toFixed(1) + '%' : '-' },
  ]
})

function goUpload() {
  const token = document.cookie.includes('session')
  if (!token) {
    ElMessage.info('请先登录后再上传数据')
    router.push('/login')
  } else {
    router.push('/user/data')
  }
}

onMounted(async () => {
  loading.value = true

  // 检查登录状态（session cookie 为 HttpOnly，JS 无法直接读取，需通过 API 判断）
  try {
    const res = await getCurrentUser()
    const user = res.data?.user || res.data
    if (user && user.username) {
      isLoggedIn.value = true
      currentUser.value = user
    }
  } catch (_) { isLoggedIn.value = false }

  try {
    // 并行加载所有公开数据
    const [summaryRes, trendRes, pieRes, corrRes, scatterRes] = await Promise.allSettled([
      getPublicSummary(),
      getPublicTrend(),
      getPublicStagePie(),
      getPublicCorrelation(),
      getPublicScatter(),
    ])

    if (summaryRes.status === 'fulfilled') {
      summary.value = summaryRes.value.data
      hasData.value = summary.value.total_records > 0
    }

    if (trendRes.status === 'fulfilled' && hasData.value) {
      const t = trendRes.value.data
      trendOption.value = {
        tooltip: { trigger: 'axis' },
        legend: { data: ['质量分', '效率%', '睡眠(小时)'], textStyle: { color: '#aaa' } },
        xAxis: { type: 'category', data: t.dates, axisLabel: { color: '#889' } },
        yAxis: [
          { type: 'value', axisLabel: { color: '#889' } },
          { type: 'value', axisLabel: { color: '#889' } },
        ],
        series: [
          { name: '质量分', type: 'line', smooth: true, data: t.quality_scores, itemStyle: { color: '#ffd04b' } },
          { name: '效率%', type: 'line', smooth: true, data: t.efficiency_pct, itemStyle: { color: '#67c23a' } },
          { name: '睡眠(小时)', type: 'line', smooth: true, yAxisIndex: 1, data: t.total_sleep_hours, itemStyle: { color: '#409eff' } },
        ],
      }
      trendReady.value = true
    }

    if (scatterRes.status === 'fulfilled' && hasData.value) {
      const s = scatterRes.value.data
      const data = s.hr_vs_quality || []
      const xs = data.map(d => d[0]), ys = data.map(d => d[1])
      const xMin = Math.min(...xs), xMax = Math.max(...xs)
      const yMin = Math.min(...ys), yMax = Math.max(...ys)
      const xPad = (xMax - xMin) * 0.08 || 1
      const yPad = (yMax - yMin) * 0.1 || 0.5
      scatterHROption.value = {
        tooltip: {},
        grid: { left: '12%', right: '5%', top: '8%', bottom: '10%' },
        xAxis: { name: '心率(bpm)', nameLocation: 'center', nameGap: 28, axisLabel: { color: '#889' }, min: xMin - xPad, max: xMax + xPad },
        yAxis: { name: '质量分', axisLabel: { color: '#889' }, min: Math.max(0, yMin - yPad), max: Math.min(10, yMax + yPad) },
        series: [{ type: 'scatter', data, symbolSize: 7, itemStyle: { color: '#ff6b6b', opacity: 0.7 } }],
      }
      scatterReady.value = true
    }

    if (pieRes.status === 'fulfilled' && hasData.value) {
      const p = pieRes.value.data
      pieOption.value = {
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, textStyle: { color: '#aaa' } },
        series: [{
          type: 'pie', radius: ['40%', '70%'], center: ['50%', '45%'], label: { color: '#ccc' },
          data: p.stages.map(s => ({
            ...s,
            itemStyle: { color: s.name === '深睡' ? '#1a5276' : s.name === '浅睡' ? '#5dade2' : s.name === 'REM' ? '#8e44ad' : '#e74c3c' },
          })),
        }],
      }
      pieReady.value = true
    }

    if (corrRes.status === 'fulfilled' && hasData.value) {
      const c = corrRes.value.data
      const fields = c.fields
      const labels = c.field_labels
      const mat = []
      fields.forEach((f1, i) => {
        fields.forEach((f2, j) => {
          mat.push([j, i, c.correlation_matrix[`${f1}|${f2}`] || 0])
        })
      })
      const xLabels = fields.map(f => labels[f] || f)
      corrOption.value = {
        tooltip: { formatter: (p) => { const xl = xLabels[p.value[0]] || ''; const yl = xLabels[p.value[1]] || ''; return `<b>${xl}</b> × <b>${yl}</b><br/>相关系数: ${p.value[2]}`; } },
        grid: { left: '18%', bottom: '15%', top: '2%', right: '5%' },
        xAxis: { type: 'category', data: xLabels, axisLabel: { color: '#889', rotate: 35, fontSize: 9 }, position: 'bottom' },
        yAxis: { type: 'category', data: xLabels, axisLabel: { color: '#889', fontSize: 9 } },
        visualMap: { min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#f46d43', '#d73027', '#a50026'] } },
        series: [{ type: 'heatmap', data: mat, label: { show: true, fontSize: 10, fontWeight: 'bold', color: (p) => { const v = p.value[2]; return Math.abs(v) > 0.5 ? '#fff' : '#222'; } }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } } }],
      }
      corrReady.value = true
    }
  } catch (e) {
    console.error('加载公开数据失败', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.chart { width: 100%; height: 400px; }
.page { padding: 10px; }
</style>
