<template>
  <div class="page">
    <h2 style="margin-bottom:20px">📊 可视化分析</h2>
    <p style="color:#889;margin-bottom:24px">基于 DATA 文件夹的睡眠数据可视化分析结果</p>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="📈 趋势图" name="trend">
        <el-card class="card-dark"><v-chart class="chart" :option="trendOption" autoresize /></el-card>
      </el-tab-pane>
      <el-tab-pane label="🎯 散点图" name="scatter">
        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <el-card class="card-dark"><template #header>心率 vs 睡眠质量</template><v-chart class="chart" :option="scatterHROption" autoresize /></el-card>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-card class="card-dark"><template #header>步数 vs 睡眠质量</template><v-chart class="chart" :option="scatterStepsOption" autoresize /></el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
      <el-tab-pane label="🔥 相关性热力图" name="correlation">
        <el-card class="card-dark"><v-chart class="chart" style="height:550px" :option="corrOption" autoresize /></el-card>
      </el-tab-pane>
      <el-tab-pane label="🍰 阶段占比" name="stage">
        <el-card class="card-dark"><v-chart class="chart" :option="pieOption" autoresize /></el-card>
      </el-tab-pane>
      <el-tab-pane label="🏗️ 睡眠结构" name="structure">
        <el-card class="card-dark"><v-chart class="chart" :option="structOption" autoresize /></el-card>
      </el-tab-pane>
    </el-tabs>

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
import { getPublicTrend, getPublicStagePie, getPublicCorrelation, getPublicScatter, getPublicSleepStructure } from '../api/sleep'

use([CanvasRenderer, LineChart, BarChart, PieChart, ScatterChart, HeatmapChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent])

const activeTab = ref('trend')
const loading = ref(true)
const hasData = ref(false)
const trendOption = ref({})
const scatterHROption = ref({})
const scatterStepsOption = ref({})
const corrOption = ref({})
const pieOption = ref({})
const structOption = ref({})

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
    }

    if (scatterRes.status === 'fulfilled') {
      const s = scatterRes.value.data
      scatterHROption.value = {
        tooltip: {}, xAxis: { name: '心率', axisLabel: { color: '#889' } },
        yAxis: { name: '质量分', axisLabel: { color: '#889' } },
        series: [{ type: 'scatter', data: s.hr_vs_quality, itemStyle: { color: '#ff6b6b' } }],
      }
      scatterStepsOption.value = {
        tooltip: {}, xAxis: { name: '步数', axisLabel: { color: '#889' } },
        yAxis: { name: '质量分', axisLabel: { color: '#889' } },
        series: [{ type: 'scatter', data: s.steps_vs_quality, itemStyle: { color: '#4ecdc4' } }],
      }
    }

    if (corrRes.status === 'fulfilled') {
      const c = corrRes.value.data
      const fields = c.fields
      const labels = c.field_labels
      const mat = []
      fields.forEach((f1, i) => { fields.forEach((f2, j) => { mat.push([j, i, c.correlation_matrix[`${f1}|${f2}`] || 0]) }) })
      corrOption.value = {
        tooltip: {}, grid: { left: '15%', bottom: '15%' },
        xAxis: { type: 'category', data: fields.map(f => labels[f] || f), axisLabel: { color: '#889', rotate: 30, fontSize: 10 } },
        yAxis: { type: 'category', data: fields.map(f => labels[f] || f), axisLabel: { color: '#889', fontSize: 10 } },
        visualMap: { min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#f46d43', '#d73027', '#a50026'] } },
        series: [{ type: 'heatmap', data: mat, label: { show: true, fontSize: 8 } }],
      }
    }

    if (pieRes.status === 'fulfilled') {
      const p = pieRes.value.data
      pieOption.value = {
        tooltip: { trigger: 'item' }, legend: { bottom: 0, textStyle: { color: '#aaa' } },
        series: [{ type: 'pie', radius: ['40%', '70%'], center: ['50%', '45%'], label: { color: '#ccc' },
          data: p.stages.map(s => ({ ...s, itemStyle: { color: s.name === '深睡' ? '#1a5276' : s.name === '浅睡' ? '#5dade2' : s.name === 'REM' ? '#8e44ad' : '#e74c3c' } })) }],
      }
    }

    if (structRes.status === 'fulfilled') {
      const s = structRes.value.data
      structOption.value = {
        tooltip: { trigger: 'axis' },
        legend: { data: ['深睡', '浅睡', 'REM', '清醒'], textStyle: { color: '#aaa' } },
        xAxis: { type: 'category', data: s.dates, axisLabel: { color: '#889' } },
        yAxis: { type: 'value', axisLabel: { color: '#889' } },
        series: [
          { name: '深睡', type: 'bar', stack: 'total', data: s.deep, itemStyle: { color: '#1a5276' } },
          { name: '浅睡', type: 'bar', stack: 'total', data: s.shallow, itemStyle: { color: '#5dade2' } },
          { name: 'REM', type: 'bar', stack: 'total', data: s.rem, itemStyle: { color: '#8e44ad' } },
          { name: '清醒', type: 'bar', stack: 'total', data: s.wake, itemStyle: { color: '#e74c3c' } },
        ],
      }
    }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
})
</script>

<style scoped>
.chart { width: 100%; height: 400px; }
.page { padding: 10px; }
</style>
