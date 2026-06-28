<template>
  <div class="viz-page">
    <div class="page-hero">
      <h2 class="page-title">📊 可视化分析</h2>
      <p class="page-subtitle">基于 DATA 文件夹的睡眠数据可视化分析结果</p>
    </div>

    <el-collapse v-model="activeSections" class="viz-collapse">
      <!-- ========== 趋势图 ========== -->
      <el-collapse-item name="trend">
        <template #title>
          <div class="section-header">
            <span class="section-icon">📈</span>
            <span class="section-label">睡眠趋势总览</span>
            <span class="section-badge">质量分 · 效率 · 睡眠时长</span>
          </div>
        </template>
        <div class="section-body">
          <v-chart class="chart chart-tall" :option="trendOption" autoresize />
        </div>
      </el-collapse-item>

      <!-- ========== 散点图 ========== -->
      <el-collapse-item name="scatter">
        <template #title>
          <div class="section-header">
            <span class="section-icon">🎯</span>
            <span class="section-label">指标关联散点图</span>
            <span class="section-badge">心率 · 步数 vs 睡眠质量</span>
          </div>
        </template>
        <div class="section-body">
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <div class="chart-card">
                <div class="chart-card-title">❤️ 心率 vs 睡眠质量</div>
                <v-chart class="chart" :option="scatterHROption" autoresize />
              </div>
            </el-col>
            <el-col :xs="24" :sm="12">
              <div class="chart-card">
                <div class="chart-card-title">👟 步数 vs 睡眠质量</div>
                <v-chart class="chart" :option="scatterStepsOption" autoresize />
              </div>
            </el-col>
          </el-row>
        </div>
      </el-collapse-item>

      <!-- ========== 相关性热力图 ========== -->
      <el-collapse-item name="correlation">
        <template #title>
          <div class="section-header">
            <span class="section-icon">🔥</span>
            <span class="section-label">多维相关性热力图</span>
            <span class="section-badge">全维度特征关联矩阵</span>
          </div>
        </template>
        <div class="section-body">
          <div class="chart-card">
            <v-chart class="chart chart-xl" :option="corrOption" autoresize />
          </div>
        </div>
      </el-collapse-item>

      <!-- ========== 阶段占比 + 睡眠结构 ========== -->
      <el-collapse-item name="stage">
        <template #title>
          <div class="section-header">
            <span class="section-icon">🍰</span>
            <span class="section-label">睡眠阶段分析</span>
            <span class="section-badge">阶段占比 · 睡眠结构</span>
          </div>
        </template>
        <div class="section-body">
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12">
              <div class="chart-card">
                <div class="chart-card-title">🥧 睡眠阶段占比</div>
                <v-chart class="chart" :option="pieOption" autoresize />
              </div>
            </el-col>
            <el-col :xs="24" :sm="12">
              <div class="chart-card" v-if="structOption && structOption.series">
                <div class="chart-card-title">🏗️ 睡眠结构堆叠图</div>
                <v-chart class="chart" :option="structOption" autoresize />
              </div>
            </el-col>
          </el-row>
        </div>
      </el-collapse-item>

      <!-- ========== 环境参数 ========== -->
      <el-collapse-item name="environment">
        <template #title>
          <div class="section-header">
            <span class="section-icon">🌡️</span>
            <span class="section-label">环境参数影响分析</span>
            <span class="section-badge">温度 · 湿度 · 噪声 · 血氧 · 体动</span>
          </div>
        </template>
        <div class="section-body">
          <el-row :gutter="16">
            <el-col :xs="24" :sm="12" :md="6">
              <div class="chart-card">
                <div class="chart-card-title">🌡️ 温度 vs 质量</div>
                <v-chart class="chart chart-sm" :option="envTempOption" autoresize />
              </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <div class="chart-card">
                <div class="chart-card-title">💧 湿度 vs 质量</div>
                <v-chart class="chart chart-sm" :option="envHumidOption" autoresize />
              </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <div class="chart-card">
                <div class="chart-card-title">🔊 噪声 vs 质量</div>
                <v-chart class="chart chart-sm" :option="envNoiseOption" autoresize />
              </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <div class="chart-card">
                <div class="chart-card-title">🫁 血氧 vs 质量</div>
                <v-chart class="chart chart-sm" :option="envSpo2Option" autoresize />
              </div>
            </el-col>
          </el-row>
          <div class="chart-card" style="margin-top:16px">
            <div class="chart-card-title">📈 环境参数日趋势（温度 / 湿度 / 噪声 / 血氧 / 体动）</div>
            <v-chart class="chart chart-tall" :option="envTrendOption" autoresize />
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <el-empty v-if="!hasData && !loading" description="暂无数据" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import { getPublicTrend, getPublicStagePie, getPublicCorrelation, getPublicScatter, getPublicSleepStructure } from '../api/sleep'

use([CanvasRenderer, LineChart, BarChart, PieChart, ScatterChart, HeatmapChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent])

const loading = ref(true)
const hasData = ref(false)

// 响应式：大屏全部展开，小屏折叠
const ALL_SECTIONS = ['trend', 'scatter', 'correlation', 'stage', 'environment']
const activeSections = ref([...ALL_SECTIONS])
const isMobile = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    activeSections.value = ['trend']
  } else {
    activeSections.value = [...ALL_SECTIONS]
  }
}

let resizeTimer = null
function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(checkMobile, 200)
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', onResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})

const trendOption = ref({})
const scatterHROption = ref({})
const scatterStepsOption = ref({})
const corrOption = ref({})
const pieOption = ref({})
const structOption = ref({})
const envTempOption = ref({})
const envHumidOption = ref({})
const envNoiseOption = ref({})
const envSpo2Option = ref({})
const envTrendOption = ref({})

onMounted(async () => {
  loading.value = true
  try {
    const [trendRes, pieRes, corrRes, scatterRes, structRes] = await Promise.allSettled([
      getPublicTrend(), getPublicStagePie(), getPublicCorrelation(), getPublicScatter(), getPublicSleepStructure(),
    ])

    if (trendRes.status === 'fulfilled') {
      const t = trendRes.value.data
      hasData.value = t.dates && t.dates.length > 0
      trendOption.value = {
        tooltip: { trigger: 'axis' },
        legend: { data: ['质量分', '效率%', '睡眠(小时)'], textStyle: { color: '#aaa' }, top: 0 },
        grid: { left: '3%', right: '5%', top: '12%', bottom: '5%' },
        xAxis: { type: 'category', data: t.dates, axisLabel: { color: '#889', rotate: 30, fontSize: 10 } },
        yAxis: [
          { type: 'value', axisLabel: { color: '#889' } },
          { type: 'value', axisLabel: { color: '#889' } },
        ],
        series: [
          { name: '质量分', type: 'line', smooth: true, data: t.quality_scores, symbol: 'circle', symbolSize: 4, itemStyle: { color: '#ffd04b' }, lineStyle: { width: 2.5 } },
          { name: '效率%', type: 'line', smooth: true, data: t.efficiency_pct, symbol: 'diamond', symbolSize: 4, itemStyle: { color: '#67c23a' }, lineStyle: { width: 2 } },
          { name: '睡眠(小时)', type: 'line', smooth: true, yAxisIndex: 1, data: t.total_sleep_hours, symbol: 'triangle', symbolSize: 4, itemStyle: { color: '#409eff' }, lineStyle: { width: 2 } },
        ],
      }
    }

    if (scatterRes.status === 'fulfilled') {
      const s = scatterRes.value.data
      const scOpt = (name, data, color) => ({
        tooltip: {},
        grid: { left: '12%', right: '5%', top: '8%', bottom: '10%' },
        xAxis: { name, nameLocation: 'center', nameGap: 28, axisLabel: { color: '#889' } },
        yAxis: { name: '质量分', axisLabel: { color: '#889' } },
        series: [{ type: 'scatter', data, symbolSize: 7, itemStyle: { color, opacity: 0.7 } }],
      })
      scatterHROption.value = scOpt('心率(bpm)', s.hr_vs_quality, '#ff6b6b')
      scatterStepsOption.value = scOpt('步数', s.steps_vs_quality, '#4ecdc4')
    }

    if (corrRes.status === 'fulfilled') {
      const c = corrRes.value.data
      const fields = c.fields, labels = c.field_labels, mat = []
      fields.forEach((f1, i) => { fields.forEach((f2, j) => { mat.push([j, i, c.correlation_matrix[`${f1}|${f2}`] || 0]) }) })
      corrOption.value = {
        tooltip: {},
        grid: { left: '18%', bottom: '12%', top: '2%', right: '5%' },
        xAxis: { type: 'category', data: fields.map(f => labels[f] || f), axisLabel: { color: '#889', rotate: 35, fontSize: 9 }, position: 'bottom' },
        yAxis: { type: 'category', data: fields.map(f => labels[f] || f), axisLabel: { color: '#889', fontSize: 9 } },
        visualMap: { min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#f46d43', '#d73027', '#a50026'] } },
        series: [{ type: 'heatmap', data: mat, label: { show: true, fontSize: 7, color: '#ccc' }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } } }],
      }
    }

    if (pieRes.status === 'fulfilled') {
      const p = pieRes.value.data
      pieOption.value = {
        tooltip: { trigger: 'item', formatter: '{b}: {c}分钟 ({d}%)' },
        legend: { bottom: 0, textStyle: { color: '#aaa', fontSize: 11 } },
        series: [{
          type: 'pie', radius: ['45%', '72%'], center: ['50%', '45%'],
          avoidLabelOverlap: false, itemStyle: { borderRadius: 6, borderColor: '#1a2a3a', borderWidth: 3 },
          label: { show: true, position: 'outside', color: '#ccc', formatter: '{b}\n{d}%' },
          emphasis: { label: { fontSize: 18, fontWeight: 'bold' } },
          data: p.stages.map(s => ({ ...s, itemStyle: { color: s.name === '深睡' ? '#1a5276' : s.name === '浅睡' ? '#5dade2' : s.name === 'REM' ? '#8e44ad' : '#e74c3c' } })),
        }],
      }
    }

    if (structRes.status === 'fulfilled') {
      const s = structRes.value.data
      structOption.value = {
        tooltip: { trigger: 'axis' },
        legend: { data: ['深睡', '浅睡', 'REM', '清醒'], textStyle: { color: '#aaa' }, top: 0 },
        grid: { left: '3%', right: '4%', top: '12%', bottom: '5%' },
        xAxis: { type: 'category', data: s.dates, axisLabel: { color: '#889', rotate: 30, fontSize: 9 } },
        yAxis: { type: 'value', axisLabel: { color: '#889' } },
        series: [
          { name: '深睡', type: 'bar', stack: 'total', data: s.deep, itemStyle: { color: '#1a5276' }, emphasis: { focus: 'series' } },
          { name: '浅睡', type: 'bar', stack: 'total', data: s.shallow, itemStyle: { color: '#5dade2' }, emphasis: { focus: 'series' } },
          { name: 'REM', type: 'bar', stack: 'total', data: s.rem, itemStyle: { color: '#8e44ad' }, emphasis: { focus: 'series' } },
          { name: '清醒', type: 'bar', stack: 'total', data: s.wake, itemStyle: { color: '#e74c3c' }, emphasis: { focus: 'series' } },
        ],
      }
    }

    // 环境参数（公开 endpoint）
    try {
      const api = (await import('../api/sleep'))
      const envRes = await api.default.get('/vis/public/environment')
      const envVsRes = await api.default.get('/vis/public/environment_vs_quality')
      const ev = envRes.data, evv = envVsRes.data
      const makeScatter = (data, name) => ({
        tooltip: {}, grid: { left: '12%', right: '5%', top: '10%', bottom: '12%' },
        xAxis: { name, nameLocation: 'center', nameGap: 25, axisLabel: { color: '#889', fontSize: 9 } },
        yAxis: { name: '质量分', axisLabel: { color: '#889', fontSize: 9 } },
        series: [{ type: 'scatter', data, symbolSize: 5, itemStyle: { color: '#409eff', opacity: 0.6 } }],
      })
      if (evv?.scatter_data) {
        envTempOption.value = makeScatter(evv.scatter_data.temperature || [], '温度(°C)')
        envHumidOption.value = makeScatter(evv.scatter_data.humidity || [], '湿度(%)')
        envNoiseOption.value = makeScatter(evv.scatter_data.noise_db || [], '噪声(dB)')
        envSpo2Option.value = makeScatter(evv.scatter_data.spo2 || [], '血氧(%)')
      }
      if (ev?.dates) {
        envTrendOption.value = {
          tooltip: { trigger: 'axis' },
          legend: { data: ['温度°C', '湿度%', '噪声dB', '血氧%', '体动'], textStyle: { color: '#aaa' }, top: 0 },
          grid: { left: '5%', right: '5%', top: '12%', bottom: '8%' },
          xAxis: { type: 'category', data: ev.dates, axisLabel: { color: '#889', rotate: 30, fontSize: 9 } },
          yAxis: [
            { type: 'value', name: '温度/湿度/血氧', axisLabel: { color: '#889', fontSize: 9 } },
            { type: 'value', name: '噪声dB', axisLabel: { color: '#889', fontSize: 9 } },
          ],
          series: [
            { name: '温度°C', type: 'line', smooth: true, data: ev.temperature, symbol: 'none', itemStyle: { color: '#e74c3c' }, lineStyle: { width: 2 } },
            { name: '湿度%', type: 'line', smooth: true, data: ev.humidity, symbol: 'none', itemStyle: { color: '#3498db' }, lineStyle: { width: 2 } },
            { name: '血氧%', type: 'line', smooth: true, data: ev.spo2, symbol: 'none', itemStyle: { color: '#2ecc71' }, lineStyle: { width: 2 } },
            { name: '噪声dB', type: 'line', smooth: true, yAxisIndex: 1, data: ev.noise_db, symbol: 'none', itemStyle: { color: '#f39c12' }, lineStyle: { width: 1.5, type: 'dashed' } },
            { name: '体动', type: 'line', smooth: true, data: ev.movement_freq, symbol: 'none', itemStyle: { color: '#9b59b6' }, lineStyle: { width: 1.5, type: 'dashed' } },
          ],
        }
      }
    } catch (_) { /* 无环境数据时静默跳过 */ }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
})
</script>

<style scoped>
/* ====== 页面容器 ====== */
.viz-page { padding: 4px; max-width: 1400px; margin: 0 auto; }

/* ====== 页面标题 ====== */
.page-hero {
  text-align: center; padding: 16px 0 24px;
  background: linear-gradient(180deg, rgba(26,42,58,0.4) 0%, transparent 100%);
  border-radius: 12px; margin-bottom: 8px;
}
.page-title { font-size: 1.8rem; font-weight: 700; color: #ffd04b; margin: 0 0 6px; letter-spacing: 1px; }
.page-subtitle { color: #7a8a9a; font-size: 0.9rem; margin: 0; }

/* ====== Collapse 美化 ====== */
.viz-collapse {
  --el-collapse-header-bg-color: #1a2a3a;
  --el-collapse-content-bg-color: #0f1923;
  border: none;
}
.viz-collapse :deep(.el-collapse-item) {
  margin-bottom: 10px;
  border: 1px solid #2a3a4a;
  border-radius: 12px;
  overflow: hidden;
  background: #1a2a3a;
  transition: all 0.3s ease;
}
.viz-collapse :deep(.el-collapse-item:hover) {
  border-color: #3a5a7a;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.viz-collapse :deep(.el-collapse-item__header) {
  height: auto !important;
  padding: 14px 20px;
  background: linear-gradient(135deg, #1e3044 0%, #1a2a3a 100%);
  border-bottom: 1px solid #2a3a4a;
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
  line-height: 1.4;
}
.viz-collapse :deep(.el-collapse-item__wrap) {
  background: #0f1923;
  border: none;
}
.viz-collapse :deep(.el-collapse-item__content) {
  padding: 20px;
}

/* 桌面端隐藏折叠箭头 */
.viz-collapse :deep(.el-collapse-item__arrow) { display: none; }

/* ====== 区块标题 ====== */
.section-header {
  display: flex; align-items: center; gap: 10px; width: 100%;
}
.section-icon { font-size: 1.3rem; }
.section-label { flex: 0 0 auto; }
.section-badge {
  margin-left: auto;
  font-size: 0.75rem; font-weight: 400; color: #5a7a9a;
  background: rgba(255,255,255,0.04); padding: 2px 10px; border-radius: 20px;
}

/* ====== 区块内容 ====== */
.section-body { padding: 4px 0; }

/* ====== 单个图表卡片 ====== */
.chart-card {
  background: #162230;
  border: 1px solid #243444;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 8px;
  transition: border-color 0.2s;
}
.chart-card:hover { border-color: #3a5a7a; }
.chart-card-title {
  color: #8899aa; font-size: 0.8rem; font-weight: 600;
  margin-bottom: 8px; padding-left: 4px; letter-spacing: 0.5px;
}

/* ====== 图表尺寸变体 ====== */
.chart { width: 100%; height: 380px; }
.chart-sm { height: 280px; }
.chart-tall { height: 450px; }
.chart-xl { height: 550px; }

/* ====== 移动端适配 ====== */
@media (max-width: 767px) {
  .viz-collapse :deep(.el-collapse-item__arrow) { display: block; }
  .section-badge { display: none; }
  .chart { height: 300px; }
  .chart-sm { height: 240px; }
  .chart-tall { height: 340px; }
  .chart-xl { height: 400px; }
  .page-title { font-size: 1.3rem; }
}
</style>
