<template>
  <div class="viz-page">
    <div class="page-hero">
      <h2 class="page-title">📊 可视化分析</h2>
      <p class="page-subtitle">基于 DATA 文件夹的睡眠数据可视化分析结果</p>
      <div v-if="modelList.length" style="margin-top:10px;display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap">
        <span style="color:#8899aa;font-size:0.85rem">🤖 选择分析模型：</span>
        <el-select v-model="selectedModel" placeholder="自动选择最佳模型" size="small" style="width:220px" @change="onModelChange">
          <el-option label="⭐ 最佳模型（自动）" value="" />
          <el-option v-for="m in modelList" :key="m.key" :label="`${m.name} (R²=${m.r2})`" :value="m.key" />
        </el-select>
        <span v-if="selectedModel" style="color:#5a7a9a;font-size:0.75rem">R²={{ modelList.find(m=>m.key===selectedModel)?.r2 }}</span>
      </div>
    </div>

    <!-- 选中模型的特征重要性 -->
    <div v-if="modelFIOption" style="margin-bottom:16px;max-width:1400px;margin-left:auto;margin-right:auto">
      <el-card class="card-dark">
        <template #header>
          <span>📊 {{ selectedModel ? modelList.find(m=>m.key===selectedModel)?.name : '最佳模型' }} — 特征重要性</span>
          <span v-if="modelInfo" style="float:right;font-size:0.75rem;color:#889">
            R²={{ modelInfo.r2 }} | MAE={{ modelInfo.mae }} | RMSE={{ modelInfo.rmse }}
          </span>
        </template>
        <v-chart class="chart" style="height:350px" :option="modelFIOption" autoresize />
      </el-card>
    </div>

    <!-- ========== 趋势图 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'trend' }">
      <div class="section-header">
        <span class="section-icon">📈</span>
        <span class="section-label">睡眠趋势总览</span>
        <span class="section-badge">质量分 · 效率 · 睡眠时长</span>
        <span class="section-fs-btn" @click.stop="toggleFs('trend')" :title="fsSection==='trend'?'退出全屏':'全屏查看'">{{ fsSection==='trend'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <v-chart class="chart chart-tall" :option="trendOption" autoresize />
      </div>
    </div>

    <!-- ========== 散点图 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'scatter' }">
      <div class="section-header">
        <span class="section-icon">🎯</span>
        <span class="section-label">指标关联散点图</span>
        <span class="section-badge">心率 · 步数 · 温度 · 噪声 vs 睡眠质量</span>
        <span class="section-fs-btn" @click.stop="toggleFs('scatter')" :title="fsSection==='scatter'?'退出全屏':'全屏查看'">{{ fsSection==='scatter'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <div class="chart-card">
          <div class="chart-card-title">❤️ 心率 vs 睡眠质量</div>
          <v-chart class="chart" :option="scatterHROption" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-title">👟 步数 vs 睡眠质量</div>
          <v-chart class="chart" :option="scatterStepsOption" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-title">🌡️ 温度 vs 睡眠质量</div>
          <v-chart class="chart" :option="scatterTempOption" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-title">🔊 噪声 vs 睡眠质量</div>
          <v-chart class="chart" :option="scatterNoiseOption" autoresize />
        </div>
      </div>
    </div>

    <!-- ========== 相关性热力图 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'correlation' }">
      <div class="section-header">
        <span class="section-icon">🔥</span>
        <span class="section-label">多维相关性热力图</span>
        <span class="section-badge">全维度特征关联矩阵（含环境参数）</span>
        <span class="section-fs-btn" @click.stop="toggleFs('correlation')" :title="fsSection==='correlation'?'退出全屏':'全屏查看'">{{ fsSection==='correlation'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <div class="chart-card">
          <v-chart class="chart chart-xl" :option="corrOption" autoresize />
        </div>
      </div>
    </div>

    <!-- ========== 阶段占比 + 睡眠结构 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'stage' }">
      <div class="section-header">
        <span class="section-icon">🍰</span>
        <span class="section-label">睡眠阶段分析</span>
        <span class="section-badge">阶段占比 · 睡眠结构</span>
        <span class="section-fs-btn" @click.stop="toggleFs('stage')" :title="fsSection==='stage'?'退出全屏':'全屏查看'">{{ fsSection==='stage'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <div class="chart-card">
          <div class="chart-card-title">🥧 睡眠阶段占比</div>
          <v-chart class="chart" :option="pieOption" autoresize />
        </div>
        <div class="chart-card" v-if="structOption && structOption.series">
          <div class="chart-card-title">🏗️ 睡眠结构堆叠图</div>
          <v-chart class="chart" :option="structOption" autoresize />
        </div>
      </div>
    </div>

    <!-- ========== 环境参数 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'environment' }">
      <div class="section-header">
        <span class="section-icon">🌡️</span>
        <span class="section-label">环境参数影响分析</span>
        <span class="section-badge">温度 · 湿度 · 噪声 · 血氧 · 体动</span>
        <span class="section-fs-btn" @click.stop="toggleFs('environment')" :title="fsSection==='environment'?'退出全屏':'全屏查看'">{{ fsSection==='environment'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <div class="chart-card">
          <div class="chart-card-title">🌡️ 温度 vs 质量</div>
          <v-chart class="chart" :option="envTempOption" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-title">💧 湿度 vs 质量</div>
          <v-chart class="chart" :option="envHumidOption" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-title">🔊 噪声 vs 质量</div>
          <v-chart class="chart" :option="envNoiseOption" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-title">🫁 血氧 vs 质量</div>
          <v-chart class="chart" :option="envSpo2Option" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-title">📈 环境参数日趋势（温度 / 湿度 / 噪声 / 血氧 / 体动）</div>
          <v-chart class="chart chart-tall" :option="envTrendOption" autoresize />
        </div>
      </div>
    </div>

    <!-- ========== 全模型对比 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'models' }">
      <div class="section-header">
        <span class="section-icon">🤖</span>
        <span class="section-label">全模型算法对比</span>
        <span class="section-badge">12种回归算法 · R²/MAE/RMSE</span>
        <span class="section-fs-btn" @click.stop="toggleFs('models')" :title="fsSection==='models'?'退出全屏':'全屏查看'">{{ fsSection==='models'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <div class="chart-card">
          <div class="chart-card-title">📊 各算法 R² 决定系数对比（越高越好）</div>
          <v-chart class="chart chart-tall" :option="modelR2Option" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-title">📋 全模型指标明细</div>
          <el-table :data="modelTableData" size="small" stripe max-height="420" style="margin-top:8px">
            <el-table-column prop="name" label="算法模型" width="180" />
            <el-table-column prop="r2" label="R²" sortable width="70">
              <template #default="{row}">
                <span :style="{color:row.r2>0.6?'#67c23a':row.r2>0.3?'#409eff':'#e6a23c',fontWeight:'bold'}">{{ row.r2 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="mae" label="MAE" sortable width="70" />
            <el-table-column prop="rmse" label="RMSE" sortable width="80" />
            <el-table-column label="评级" width="60">
              <template #default="{row}">
                <el-tag :type="row.r2>0.6?'success':row.r2>0.3?'primary':'warning'" size="small">{{ row.r2>0.6?'优':row.r2>0.3?'中':'弱' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="chart-card" style="margin-top:8px">
          <div class="chart-card-title">📈 各算法 MAE / RMSE 误差对比（越低越好）</div>
          <v-chart class="chart chart-tall" :option="modelErrorOption" autoresize />
        </div>
      </div>
    </div>

    <el-empty v-if="!hasData && !loading" description="暂无数据" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import { getPublicTrend, getPublicStagePie, getPublicCorrelation, getPublicScatter, getPublicSleepStructure, getPublicModelComparison } from '../api/sleep'
import { formatMinutes } from '../utils/format'

use([CanvasRenderer, LineChart, BarChart, PieChart, ScatterChart, HeatmapChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent])

const loading = ref(true)
const hasData = ref(false)

// 全屏切换
const fsSection = ref(null)
function toggleFs(name) {
  fsSection.value = fsSection.value === name ? null : name
}

const trendOption = ref({})
const scatterHROption = ref({})
const scatterStepsOption = ref({})
const scatterTempOption = ref({})
const scatterNoiseOption = ref({})
const corrOption = ref({})
const pieOption = ref({})
const structOption = ref({})
const envTempOption = ref({})
const envHumidOption = ref({})
const envNoiseOption = ref({})
const envSpo2Option = ref({})
const envTrendOption = ref({})

// 模型对比
const modelR2Option = ref({})
const modelErrorOption = ref({})
const modelTableData = ref([])
const modelList = ref([])
const selectedModel = ref('')
const modelFIOption = ref(null)
const modelInfo = ref(null)
const cachedModelData = ref(null)

function onModelChange(key) {
  if (!cachedModelData.value) return
  const data = cachedModelData.value
  const fi = data.per_model_fi || {}
  const mc = data.model_comparison || {}
  const modelKey = key || data.best_model || ''
  const fiData = fi[modelKey]
  const modelStats = mc[modelKey]
  if (!fiData || !modelStats) { modelFIOption.value = null; modelInfo.value = null; return }

  modelInfo.value = { r2: modelStats.r2, mae: modelStats.mae, rmse: modelStats.rmse }

  // Build feature importance bar chart
  const entries = Object.entries(fiData).sort((a,b)=>Math.abs(b[1])-Math.abs(a[1]))
  const names = entries.map(e=>e[0])
  const vals = entries.map(e=>e[1])
  const colors = vals.map(v=>v>=0?'#67c23a':'#f56c6c')
  modelFIOption.value = {
    tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:(p)=>{const r=p[0];return `<b>${r.name}</b><br/>重要性: ${r.value.toFixed(4)}`}},
    grid:{left:'3%',right:'8%',top:'3%',bottom:'8%',containLabel:true},
    xAxis:{type:'value',name:'特征重要性',axisLabel:{color:'#889'}},
    yAxis:{type:'category',data:names.reverse(),axisLabel:{color:'#ccc',fontSize:10},inverse:true},
    series:[{type:'bar',data:vals.reverse().map((v,i)=>({value:v,itemStyle:{color:colors.reverse()[i],borderRadius:[0,4,4,0]}})),barMaxWidth:22,label:{show:true,position:'right',color:'#aaa',fontSize:9,formatter:p=>p.value.toFixed(4)}}]
  }
  // Also update R² chart highlight
  if (modelTableData.value.length) {
    const r2vals = modelTableData.value.map(e => e.r2)
    const hColors = r2vals.map((v, i) => {
      const k = modelTableData.value[i].key
      if (k === modelKey) return '#67c23a'
      return v > 0.6 ? '#409eff' : v > 0.3 ? '#e6a23c' : '#909399'
    })
    modelR2Option.value = {
      ...modelR2Option.value,
      series: [{
        type: 'bar', data: r2vals.reverse().map((v, i) => ({
          value: v,
          itemStyle: { color: hColors.reverse()[i], borderRadius: [0, 4, 4, 0] }
        })),
        label: { show: true, position: 'right', color: '#aaa', fontSize: 10, formatter: '{c}' },
        barMaxWidth: 28,
      }],
    }
  }
}

// 构建散点图配置，自动缩放坐标轴
function buildScatterOption(name, data, color) {
  if (!data || !data.length) return {}
  const xs = data.map(d => d[0]), ys = data.map(d => d[1])
  const xMin = Math.min(...xs), xMax = Math.max(...xs)
  const yMin = Math.min(...ys), yMax = Math.max(...ys)
  const xPad = (xMax - xMin) * 0.08 || 1
  const yPad = (yMax - yMin) * 0.1 || 0.5
  return {
    tooltip:{},
    grid:{left:'12%',right:'5%',top:'8%',bottom:'10%'},
    xAxis:{name,nameLocation:'center',nameGap:28,axisLabel:{color:'#889'},min:xMin-xPad,max:xMax+xPad},
    yAxis:{name:'质量分',axisLabel:{color:'#889'},min:Math.max(0,yMin-yPad),max:Math.min(10,yMax+yPad)},
    series:[{type:'scatter',data,symbolSize:7,itemStyle:{color,opacity:0.7}}],
  }
}

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
      scatterHROption.value = buildScatterOption('心率(bpm)', s.hr_vs_quality, '#ff6b6b')
      scatterStepsOption.value = buildScatterOption('步数', s.steps_vs_quality, '#4ecdc4')
      scatterTempOption.value = buildScatterOption('温度(°C)', s.temperature_vs_quality||[], '#e74c3c')
      scatterNoiseOption.value = buildScatterOption('噪声(dB)', s.noise_vs_quality||[], '#f39c12')
    }

    if (corrRes.status === 'fulfilled') {
      const c = corrRes.value.data
      const fields = c.fields, labels = c.field_labels, mat = []
      fields.forEach((f1, i) => { fields.forEach((f2, j) => { mat.push([j, i, c.correlation_matrix[`${f1}|${f2}`] || 0]) }) })
      const xLabels = fields.map(f => labels[f] || f)
      corrOption.value = {
        tooltip: { formatter: (p) => { const xl = xLabels[p.value[0]] || ''; const yl = xLabels[p.value[1]] || ''; return `<b>X: ${xl}</b><br/><b>Y: ${yl}</b><br/>相关系数: ${(p.value[2]||0).toFixed(4)}`; } },
        grid: { left: '18%', bottom: '12%', top: '2%', right: '5%' },
        xAxis: { type: 'category', data: xLabels, axisLabel: { color: '#889', rotate: 35, fontSize: 9 }, position: 'bottom', name: '特征', nameTextStyle: {color:'#889'} },
        yAxis: { type: 'category', data: xLabels, axisLabel: { color: '#889', fontSize: 9 }, name: '特征', nameTextStyle: {color:'#889'} },
        visualMap: { min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#f46d43', '#d73027', '#a50026'] } },
        series: [{
          type: 'heatmap', data: mat,
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
        }],
      }
    }

    if (pieRes.status === 'fulfilled') {
      const p = pieRes.value.data
      pieOption.value = {
        tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${formatMinutes(p.value)} (${p.percent}%)` },
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
      const makeScatter = (data, name) => {
        if (!data || !data.length) return {}
        const xs=data.map(d=>d[0]), ys=data.map(d=>d[1])
        const xMin=Math.min(...xs), xMax=Math.max(...xs)
        const yMin=Math.min(...ys), yMax=Math.max(...ys)
        const xPad=(xMax-xMin)*0.08||1, yPad=(yMax-yMin)*0.1||0.5
        return {
          tooltip:{}, grid:{left:'12%',right:'5%',top:'10%',bottom:'12%'},
          xAxis:{name,nameLocation:'center',nameGap:25,axisLabel:{color:'#889',fontSize:9},min:xMin-xPad,max:xMax+xPad},
          yAxis:{name:'质量分',axisLabel:{color:'#889',fontSize:9},min:Math.max(0,yMin-yPad),max:Math.min(10,yMax+yPad)},
          series:[{type:'scatter',data,symbolSize:5,itemStyle:{color:'#409eff',opacity:0.6}}],
        }
      }
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

    // 全模型对比数据
    try {
      const modelRes = await getPublicModelComparison()
      const mc = modelRes.data?.model_comparison
      if (mc) {
        cachedModelData.value = modelRes.data
        const entries = Object.entries(mc)
          .filter(([, v]) => v && typeof v.r2 === 'number')
          .map(([key, val]) => ({
            key,
            name: val.name || key,
            r2: val.r2 ?? 0,
            mae: val.mae ?? 0,
            rmse: val.rmse ?? 0,
          }))
          .sort((a, b) => (b.r2 || 0) - (a.r2 || 0))
        modelTableData.value = entries
        modelList.value = entries
        // 默认展示最佳模型特征重要性
        onModelChange('')

        const names = entries.map(e => e.name)
        const r2vals = entries.map(e => e.r2)
        const colors = r2vals.map(v => v > 0.6 ? '#67c23a' : v > 0.3 ? '#409eff' : '#e6a23c')
        modelR2Option.value = {
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: '3%', right: '8%', top: '5%', bottom: '8%', containLabel: true },
          xAxis: { type: 'value', name: 'R²', max: 1, axisLabel: { color: '#889' } },
          yAxis: { type: 'category', data: names.reverse(), axisLabel: { color: '#ccc', fontSize: 11 }, inverse: true },
          series: [{
            type: 'bar', data: r2vals.reverse().map((v, i) => ({
              value: v,
              itemStyle: { color: colors.reverse()[i], borderRadius: [0, 4, 4, 0] }
            })),
            label: { show: true, position: 'right', color: '#aaa', fontSize: 10, formatter: '{c}' },
            barMaxWidth: 28,
          }],
        }

        const maeVals = entries.map(e => e.mae)
        const rmseVals = entries.map(e => e.rmse)
        modelErrorOption.value = {
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          legend: { data: ['MAE', 'RMSE'], textStyle: { color: '#aaa' }, top: 0 },
          grid: { left: '3%', right: '5%', top: '12%', bottom: '8%', containLabel: true },
          xAxis: { type: 'category', data: names, axisLabel: { color: '#ccc', fontSize: 10, rotate: 30 } },
          yAxis: { type: 'value', axisLabel: { color: '#889' } },
          series: [
            { name: 'MAE', type: 'bar', data: maeVals, itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] }, barGap: '10%', barMaxWidth: 20 },
            { name: 'RMSE', type: 'bar', data: rmseVals, itemStyle: { color: '#e6a23c', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 20 },
          ],
        }
      }
    } catch (_) { /* 模型对比加载失败静默跳过 */ }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
})
</script>

<style scoped>
.viz-page { padding: 4px; max-width: 1400px; margin: 0 auto; }
.page-hero { text-align: center; padding: 16px 0 24px; background: linear-gradient(180deg, rgba(26,42,58,0.4) 0%, transparent 100%); border-radius: 12px; margin-bottom: 8px; }
.page-title { font-size: 1.8rem; font-weight: 700; color: #ffd04b; margin: 0 0 6px; letter-spacing: 1px; }
.page-subtitle { color: #7a8a9a; font-size: 0.9rem; margin: 0; }

/* ====== 可视化区块 ====== */
.viz-section { margin-bottom: 10px; border: 1px solid #2a3a4a; border-radius: 12px; overflow: hidden; background: #1a2a3a; transition: all 0.3s ease; }
.viz-section:hover { border-color: #3a5a7a; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
.viz-section .section-header {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 14px 20px; background: linear-gradient(135deg, #1e3044 0%, #1a2a3a 100%);
  border-bottom: 1px solid #2a3a4a; font-size: 15px; font-weight: 600;
  color: #e0e0e0; line-height: 1.4; cursor: default; user-select: none;
}
.section-icon { font-size: 1.3rem; flex: 0 0 auto; }
.section-label { flex: 0 0 auto; }
.section-badge { margin-left: auto; font-size: 0.75rem; font-weight: 400; color: #5a7a9a; background: rgba(255,255,255,0.04); padding: 2px 10px; border-radius: 20px; }
.section-fs-btn {
  cursor: pointer; font-size: 1.1rem; color: #889; padding: 4px 8px; border-radius: 6px;
  transition: all 0.2s; margin-left: 8px; flex: 0 0 auto;
}
.section-fs-btn:hover { color: #ffd04b; background: rgba(255,208,75,0.1); }
.section-body { padding: 20px; }

/* ====== 全屏模式 ====== */
.viz-fullscreen {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999;
  margin: 0; border-radius: 0; border: none; max-width: none;
  background: #0f1923; display: flex; flex-direction: column;
}
.viz-fullscreen .section-header { border-bottom-color: #3a5a7a; }
.viz-fullscreen .section-body { flex: 1; overflow-y: auto; padding: 20px; }
.viz-fullscreen .chart { height: calc(100vh - 220px) !important; min-height: 400px; }
.viz-fullscreen .chart-tall { height: calc(100vh - 200px) !important; min-height: 450px; }
.viz-fullscreen .chart-xl { height: calc(100vh - 180px) !important; min-height: 500px; }

.chart-card { background: #162230; border: 1px solid #243444; border-radius: 10px; padding: 12px; margin-bottom: 12px; transition: border-color 0.2s; }
.chart-card:hover { border-color: #3a5a7a; }
.chart-card-title { color: #8899aa; font-size: 0.8rem; font-weight: 600; margin-bottom: 8px; padding-left: 4px; letter-spacing: 0.5px; }

.chart { width: 100%; height: 380px; }
.chart-tall { height: 450px; }
.chart-xl { height: 550px; }

@media (max-width: 767px) {
  .section-badge { display: none; }
  .chart { height: 300px; } .chart-tall { height: 340px; } .chart-xl { height: 400px; }
  .page-title { font-size: 1.3rem; }
}
</style>
