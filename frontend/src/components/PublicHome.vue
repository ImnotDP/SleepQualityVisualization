<template>
  <div class="dashboard">
    <!-- ===== 顶部标题栏 ===== -->
    <header class="dash-header">
      <div class="dash-header-left">
        <span class="dash-logo">🌙</span>
        <span class="dash-title">睡眠质量可视化分析大屏</span>
        <el-tag size="small" type="warning" effect="dark" class="dash-tag">12种ML算法</el-tag>
        <el-tag size="small" effect="dark" class="dash-tag-sub">DeepSeek AI</el-tag>
      </div>
      <div class="dash-header-right">
        <span class="dash-time">{{ nowTime }}</span>
        <template v-if="!isLoggedIn">
          <el-button type="warning" size="small" round @click="$router.push('/login')">登 录</el-button>
          <el-button size="small" round class="btn-ghost" @click="$router.push('/register')">注 册</el-button>
        </template>
        <template v-else>
          <span class="dash-user">{{ currentUser?.username }}</span>
          <el-button size="small" round class="btn-ghost" @click="$router.push('/user/data')">📤 上传数据</el-button>
        </template>
      </div>
    </header>

    <!-- ===== 统计指标条 ===== -->
    <div class="dash-stats" v-if="summary">
      <div class="dash-stat-item" v-for="c in cards" :key="c.label">
        <span class="dash-stat-icon">{{ c.icon }}</span>
        <div class="dash-stat-info">
          <span class="dash-stat-val">{{ c.value }}</span>
          <span class="dash-stat-lbl">{{ c.label }}</span>
        </div>
      </div>
    </div>

    <!-- ===== 主仪表盘区域 ===== -->
    <div class="dash-grid">
      <!-- 左上：睡眠阶段占比 -->
      <div class="dash-panel dash-panel--pie" v-if="pieReady">
        <div class="dash-panel-head">
          <span class="dash-panel-dot"></span>
          <span>🍰 睡眠阶段占比</span>
        </div>
        <v-chart class="dash-chart" :option="pieOption" autoresize />
      </div>

      <!-- 中上：睡眠质量趋势（核心大图） -->
      <div class="dash-panel dash-panel--trend" v-if="trendReady">
        <div class="dash-panel-head">
          <span class="dash-panel-dot dash-panel-dot--gold"></span>
          <span>📈 睡眠质量趋势总览</span>
          <el-tag size="small" type="warning" effect="dark">核心指标</el-tag>
        </div>
        <v-chart class="dash-chart" :option="trendOption" autoresize />
      </div>

      <!-- 右上：心率 vs 睡眠质量 -->
      <div class="dash-panel dash-panel--hr" v-if="scatterReady">
        <div class="dash-panel-head">
          <span class="dash-panel-dot dash-panel-dot--red"></span>
          <span>🎯 心率 vs 睡眠质量</span>
        </div>
        <v-chart class="dash-chart" :option="scatterHROption" autoresize />
      </div>

      <!-- 左下：睡眠结构堆叠图（新增） -->
      <div class="dash-panel dash-panel--struct" v-if="structReady">
        <div class="dash-panel-head">
          <span class="dash-panel-dot dash-panel-dot--purple"></span>
          <span>🏗️ 睡眠结构变化</span>
        </div>
        <v-chart class="dash-chart" :option="structOption" autoresize />
      </div>

      <!-- 中下：相关性热力图 -->
      <div class="dash-panel dash-panel--corr" v-if="corrReady">
        <div class="dash-panel-head">
          <span class="dash-panel-dot dash-panel-dot--blue"></span>
          <span>🔥 多维特征相关性热力图</span>
        </div>
        <v-chart class="dash-chart" :option="corrOption" autoresize />
      </div>

      <!-- 右下：步数 vs 睡眠质量（新增） -->
      <div class="dash-panel dash-panel--steps" v-if="stepsReady">
        <div class="dash-panel-head">
          <span class="dash-panel-dot dash-panel-dot--green"></span>
          <span>👟 步数 vs 睡眠质量</span>
        </div>
        <v-chart class="dash-chart" :option="scatterStepsOption" autoresize />
      </div>
    </div>

    <!-- ===== 底部信息栏（新增） ===== -->
    <div class="dash-footer" v-if="hasData">
      <div class="dash-footer-item" v-if="bestModel.name">
        <span class="footer-icon">🏆</span>
        <span class="footer-label">最佳模型</span>
        <span class="footer-val">{{ bestModel.name }}</span>
        <span class="footer-sub">R²={{ bestModel.r2 }}</span>
      </div>
      <div class="dash-footer-item">
        <span class="footer-icon">🔬</span>
        <span class="footer-label">算法引擎</span>
        <span class="footer-val">12种回归 + 3种分类</span>
      </div>
      <div class="dash-footer-item">
        <span class="footer-icon">🤖</span>
        <span class="footer-label">AI 增强</span>
        <span class="footer-val">DeepSeek 大模型</span>
      </div>
      <div class="dash-footer-item">
        <span class="footer-icon">📊</span>
        <span class="footer-label">数据来源</span>
        <span class="footer-val">小米手环 Zepp App</span>
      </div>
      <div class="dash-footer-item dash-footer-item--link" @click="$router.push('/vis')">
        <span>📈 查看更多可视化分析 →</span>
      </div>
    </div>

    <!-- 空数据 -->
    <el-empty v-if="!hasData && !loading" description="暂无示例数据">
      <el-button type="primary" @click="goUpload">📤 上传数据</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import { getPublicSummary, getPublicTrend, getPublicStagePie, getPublicCorrelation, getPublicScatter, getPublicSleepStructure, getPublicModelComparison, getCurrentUser } from '../api/sleep'
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
const structReady = ref(false)
const stepsReady = ref(false)
const bestModel = ref({ name: '', r2: '' })

const trendOption = ref({})
const scatterHROption = ref({})
const scatterStepsOption = ref({})
const pieOption = ref({})
const corrOption = ref({})
const structOption = ref({})

// ---- 实时时钟 ----
const nowTime = ref('')
let clockTimer = null
function tick() {
  const d = new Date()
  nowTime.value = d.toLocaleString('zh-CN', { hour12: false })
}

// ---- 统计卡片 ----
const cardIcons = ['📅', '⭐', '😴', '⚡']
const cards = computed(() => {
  if (!summary.value) return []
  const s = summary.value
  const vals = [
    { label: '记录天数', value: s.total_records || 0 },
    { label: '平均质量分', value: s.avg_quality_score || '-' },
    { label: '平均睡眠', value: formatMinutes(s.avg_sleep_minutes) || '-' },
    { label: '平均效率', value: s.avg_efficiency ? (s.avg_efficiency * 100).toFixed(1) + '%' : '-' },
  ]
  return vals.map((v, i) => ({ ...v, icon: cardIcons[i] || '📊' }))
})

function goUpload() {
  if (!isLoggedIn.value) {
    ElMessage.info('请先登录后再上传数据')
    router.push('/login')
  } else {
    router.push('/user/data')
  }
}

onMounted(async () => {
  tick()
  clockTimer = setInterval(tick, 1000)
  loading.value = true

  try {
    const res = await getCurrentUser()
    const user = res.data?.user || res.data
    if (user && user.username) {
      isLoggedIn.value = true
      currentUser.value = user
    }
  } catch (_) { isLoggedIn.value = false }

  try {
    const [summaryRes, trendRes, pieRes, corrRes, scatterRes, structRes, modelRes] = await Promise.allSettled([
      getPublicSummary(), getPublicTrend(), getPublicStagePie(), getPublicCorrelation(), getPublicScatter(),
      getPublicSleepStructure(), getPublicModelComparison(),
    ])

    if (summaryRes.status === 'fulfilled') {
      summary.value = summaryRes.value.data
      hasData.value = summary.value.total_records > 0
    }

    if (trendRes.status === 'fulfilled' && hasData.value) {
      const t = trendRes.value.data
      trendOption.value = {
        tooltip: { trigger: 'axis' },
        legend: { data: ['质量分', '效率%', '睡眠(小时)'], textStyle: { color: '#aaa' }, top: 0 },
        grid: { left: '3%', right: '5%', top: '14%', bottom: '3%' },
        xAxis: { type: 'category', data: t.dates, axisLabel: { color: '#889', rotate: 25, fontSize: 10 } },
        yAxis: [
          { type: 'value', axisLabel: { color: '#889' } },
          { type: 'value', axisLabel: { color: '#889' } },
        ],
        series: [
          { name: '质量分', type: 'line', smooth: true, data: t.quality_scores, symbol: 'circle', symbolSize: 4, itemStyle: { color: '#ffd04b' }, lineStyle: { width: 2.5 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(255,208,75,0.25)' }, { offset: 1, color: 'rgba(255,208,75,0.02)' }] } } },
          { name: '效率%', type: 'line', smooth: true, data: t.efficiency_pct, symbol: 'diamond', symbolSize: 4, itemStyle: { color: '#67c23a' }, lineStyle: { width: 2 } },
          { name: '睡眠(小时)', type: 'line', smooth: true, yAxisIndex: 1, data: t.total_sleep_hours, symbol: 'triangle', symbolSize: 4, itemStyle: { color: '#409eff' }, lineStyle: { width: 2 } },
        ],
      }
      trendReady.value = true
    }

    if (scatterRes.status === 'fulfilled' && hasData.value) {
      const s = scatterRes.value.data
      const data = s.hr_vs_quality || []
      const xs = data.map(d => d[0]), ys = data.map(d => d[1])
      const xMin = Math.min(...xs), xMax = Math.max(...xs), yMin = Math.min(...ys), yMax = Math.max(...ys)
      const xPad = (xMax - xMin) * 0.08 || 1, yPad = (yMax - yMin) * 0.1 || 0.5
      scatterHROption.value = {
        tooltip: {},
        grid: { left: '12%', right: '5%', top: '8%', bottom: '10%' },
        xAxis: { name: '心率(bpm)', nameLocation: 'center', nameGap: 28, axisLabel: { color: '#889' }, min: xMin - xPad, max: xMax + xPad },
        yAxis: { name: '质量分', axisLabel: { color: '#889' }, min: Math.max(0, yMin - yPad), max: Math.min(10, yMax + yPad) },
        series: [{ type: 'scatter', data, symbolSize: 7, itemStyle: { color: '#ff6b6b', opacity: 0.7 } }],
      }
      scatterReady.value = true
    }

    // ---- 步数散点图（复用 scatterRes 数据） ----
    if (scatterRes.status === 'fulfilled' && hasData.value) {
      const s2 = scatterRes.value.data
      const data2 = s2.steps_vs_quality || []
      if (data2.length) {
        const xs2 = data2.map(d => d[0]), ys2 = data2.map(d => d[1])
        const xMin2 = Math.min(...xs2), xMax2 = Math.max(...xs2), yMin2 = Math.min(...ys2), yMax2 = Math.max(...ys2)
        const xPad2 = (xMax2 - xMin2) * 0.08 || 100, yPad2 = (yMax2 - yMin2) * 0.1 || 0.5
        scatterStepsOption.value = {
          tooltip: {},
          grid: { left: '14%', right: '5%', top: '8%', bottom: '10%' },
          xAxis: { name: '步数', nameLocation: 'center', nameGap: 28, axisLabel: { color: '#889' }, min: Math.max(0, xMin2 - xPad2), max: xMax2 + xPad2 },
          yAxis: { name: '质量分', axisLabel: { color: '#889' }, min: Math.max(0, yMin2 - yPad2), max: Math.min(10, yMax2 + yPad2) },
          series: [{ type: 'scatter', data: data2, symbolSize: 7, itemStyle: { color: '#4ecdc4', opacity: 0.7 } }],
        }
        stepsReady.value = true
      }
    }

    // ---- 睡眠结构堆叠图 ----
    if (structRes.status === 'fulfilled' && hasData.value) {
      const st = structRes.value.data
      structOption.value = {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { data: ['深睡', '浅睡', 'REM', '清醒'], textStyle: { color: '#aaa', fontSize: 9 }, top: 0 },
        grid: { left: '3%', right: '4%', top: '12%', bottom: '3%' },
        xAxis: { type: 'category', data: st.dates || [], axisLabel: { color: '#889', rotate: 20, fontSize: 8 } },
        yAxis: { type: 'value', name: '分钟', axisLabel: { color: '#889', fontSize: 9 } },
        series: [
          { name: '深睡', type: 'bar', stack: 'total', data: st.deep || [], itemStyle: { color: '#1a5276' }, barMaxWidth: 20 },
          { name: '浅睡', type: 'bar', stack: 'total', data: st.shallow || [], itemStyle: { color: '#5dade2' }, barMaxWidth: 20 },
          { name: 'REM', type: 'bar', stack: 'total', data: st.rem || [], itemStyle: { color: '#8e44ad' }, barMaxWidth: 20 },
          { name: '清醒', type: 'bar', stack: 'total', data: st.wake || [], itemStyle: { color: '#e74c3c' }, barMaxWidth: 20 },
        ],
      }
      structReady.value = true
    }

    // ---- 模型对比信息 ----
    if (modelRes.status === 'fulfilled') {
      const mc = modelRes.value.data
      const comp = mc.model_comparison || {}
      let bestKey = mc.best_model || ''
      let bestR2 = -Infinity
      if (!bestKey || !comp[bestKey]) {
        for (const [k, v] of Object.entries(comp)) {
          if (v.r2 > bestR2) { bestR2 = v.r2; bestKey = k }
        }
      }
      const bestStats = comp[bestKey]
      if (bestStats) {
        bestModel.value = { name: bestStats.name || bestKey, r2: bestStats.r2 != null ? Number(bestStats.r2).toFixed(3) : '-' }
      }
    }

    if (pieRes.status === 'fulfilled' && hasData.value) {
      const p = pieRes.value.data
      pieOption.value = {
        tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${formatMinutes(p.value)} (${p.percent}%)` },
        legend: { bottom: 0, textStyle: { color: '#aaa', fontSize: 10 } },
        series: [{
          type: 'pie', radius: ['45%', '72%'], center: ['50%', '43%'],
          avoidLabelOverlap: false, itemStyle: { borderRadius: 4, borderColor: '#0f1923', borderWidth: 2 },
          label: { show: true, position: 'outside', color: '#ccc', formatter: '{b}\n{d}%' },
          data: p.stages.map(s => ({ ...s, itemStyle: { color: s.name === '深睡' ? '#1a5276' : s.name === '浅睡' ? '#5dade2' : s.name === 'REM' ? '#8e44ad' : '#e74c3c' } })),
        }],
      }
      pieReady.value = true
    }

    if (corrRes.status === 'fulfilled' && hasData.value) {
      const c = corrRes.value.data
      const fields = c.fields, labels = c.field_labels, mat = []
      fields.forEach((f1, i) => { fields.forEach((f2, j) => { mat.push([j, i, c.correlation_matrix[`${f1}|${f2}`] || 0]) }) })
      const xLabels = fields.map(f => labels[f] || f)
      corrOption.value = {
        tooltip: { formatter: (p) => { const xl = xLabels[p.value[0]] || ''; const yl = xLabels[p.value[1]] || ''; return `<b>X: ${xl}</b><br/><b>Y: ${yl}</b><br/>相关系数: ${(p.value[2]||0).toFixed(4)}`; } },
        grid: { left: '16%', bottom: '12%', top: '2%', right: '5%' },
        xAxis: { type: 'category', data: xLabels, axisLabel: { color: '#889', rotate: 35, fontSize: 9 }, position: 'bottom', name: '特征', nameTextStyle: {color:'#889'} },
        yAxis: { type: 'category', data: xLabels, axisLabel: { color: '#889', fontSize: 9 }, name: '特征', nameTextStyle: {color:'#889'} },
        visualMap: { min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#f46d43', '#d73027', '#a50026'] } },
        series: [{ type: 'heatmap', data: mat, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } } }],
      }
      corrReady.value = true
    }
  } catch (e) {
    console.error('加载公开数据失败', e)
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style scoped>
/* ================================================================
   DASHBOARD BIG SCREEN — 大屏仪表盘样式
   ================================================================ */
.dashboard {
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

/* ---- 顶部标题栏 ---- */
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 16px;
  background: linear-gradient(180deg, rgba(26,42,58,0.95), rgba(15,25,35,0.9));
  border: 1px solid #2a3a4a;
  border-radius: 8px;
  flex-shrink: 0;
}
.dash-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dash-logo { font-size: 1.4rem; }
.dash-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #ffd04b;
  letter-spacing: 2px;
}
.dash-tag { margin-left: 4px; }
.dash-tag-sub {
  background: rgba(64,158,255,0.15) !important;
  border-color: rgba(64,158,255,0.3) !important;
  color: #409eff !important;
}
.dash-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.dash-time {
  color: #5a8aaa;
  font-size: 0.85rem;
  font-family: 'Consolas', monospace;
}
.dash-user {
  color: #b0b8c4;
  font-size: 0.9rem;
  font-weight: 500;
}
.btn-ghost {
  border: 1px solid #2a3a4a !important;
  color: #8899aa !important;
  background: transparent !important;
}
.btn-ghost:hover {
  border-color: #ffd04b66 !important;
  color: #ffd04b !important;
}

/* ---- 统计指标条 ---- */
.dash-stats {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.dash-stat-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(26,42,58,0.9), rgba(21,37,53,0.9));
  border: 1px solid #2a3a4a;
  border-radius: 8px;
}
.dash-stat-icon {
  font-size: 1.6rem;
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,208,75,0.08);
  border-radius: 8px;
  flex-shrink: 0;
}
.dash-stat-info {
  display: flex;
  flex-direction: column;
}
.dash-stat-val {
  font-size: 1.4rem;
  font-weight: 700;
  color: #ffd04b;
  line-height: 1.2;
  font-family: 'Consolas', monospace;
}
.dash-stat-lbl {
  font-size: 0.75rem;
  color: #667788;
}

/* ---- 主仪表盘网格 ---- */
.dash-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 8px;
  min-height: 0;
}
.dash-panel {
  background: rgba(26,42,58,0.85);
  border: 1px solid #2a3a4a;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  backdrop-filter: blur(4px);
}
.dash-panel--pie    { grid-column: 1; grid-row: 1; }
.dash-panel--struct { grid-column: 1; grid-row: 2; }
.dash-panel--trend  { grid-column: 2; grid-row: 1; }
.dash-panel--corr   { grid-column: 2; grid-row: 2; }
.dash-panel--hr     { grid-column: 3; grid-row: 1; }
.dash-panel--steps  { grid-column: 3; grid-row: 2; }
.dash-panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-shrink: 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: #ccd6e0;
}
.dash-panel-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #409eff;
  box-shadow: 0 0 6px #409eff88;
  flex-shrink: 0;
}
.dash-panel-dot--gold {
  background: #ffd04b;
  box-shadow: 0 0 6px #ffd04b88;
}
.dash-panel-dot--red {
  background: #ff6b6b;
  box-shadow: 0 0 6px #ff6b6b88;
}
.dash-panel-dot--blue {
  background: #409eff;
  box-shadow: 0 0 6px #409eff88;
}
.dash-panel-dot--purple {
  background: #a855f7;
  box-shadow: 0 0 6px #a855f788;
}
.dash-panel-dot--green {
  background: #4ecdc4;
  box-shadow: 0 0 6px #4ecdc488;
}

/* ---- 图表容器 ---- */
.dash-chart {
  flex: 1;
  min-height: 0;
}
.dash-chart--big {
  /* 中间大图 */
}
.dash-chart--heat {
  /* 底部热力图 */
}

/* ---- 底部信息栏 ---- */
.dash-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  background: rgba(26,42,58,0.85);
  border: 1px solid #2a3a4a;
  border-radius: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.dash-footer-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  color: #8899aa;
  white-space: nowrap;
}
.footer-icon { font-size: 1rem; }
.footer-label { color: #556677; }
.footer-val { color: #ccd6e0; font-weight: 600; }
.footer-sub { color: #ffd04b; font-weight: 700; font-family: 'Consolas', monospace; }
.dash-footer-item--link {
  margin-left: auto;
  color: #409eff;
  cursor: pointer;
  font-weight: 500;
  transition: color 0.2s;
}
.dash-footer-item--link:hover { color: #ffd04b; }

/* ---- Element Plus empty 覆盖 ---- */
.dashboard > .el-empty {
  margin-top: 60px;
}

/* ================================================================
   RESPONSIVE
   ================================================================ */
@media (max-width: 1100px) {
  .dash-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto;
  }
  .dash-panel--pie    { grid-column: 1; grid-row: 2; }
  .dash-panel--struct { grid-column: 1; grid-row: 3; }
  .dash-panel--trend  { grid-column: 1 / -1; grid-row: 1; }
  .dash-panel--corr   { grid-column: 1 / -1; grid-row: 5; }
  .dash-panel--hr     { grid-column: 2; grid-row: 2; }
  .dash-panel--steps  { grid-column: 2; grid-row: 3; }
  .dash-chart { min-height: 240px; }
}
@media (max-width: 700px) {
  .dashboard { height: auto; overflow: visible; }
  .dash-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }
  .dash-panel--pie,
  .dash-panel--struct,
  .dash-panel--trend,
  .dash-panel--corr,
  .dash-panel--hr,
  .dash-panel--steps { grid-column: 1; grid-row: auto; }
  .dash-panel { min-height: 280px; }
  .dash-stats { flex-wrap: wrap; }
  .dash-stat-item { flex: 1 1 45%; }
  .dash-header { flex-wrap: wrap; gap: 8px; }
  .dash-footer { gap: 8px; }
  .dash-footer-item--link { margin-left: 0; }
}
</style>
