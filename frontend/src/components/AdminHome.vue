<template>
  <div class="page">
    <h2 style="margin-bottom:20px">🛡️ 管理员首页</h2>

    <!-- 模型选择 -->
    <div v-if="modelList.length" style="margin-bottom:16px;display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap">
      <span style="color:#8899aa;font-size:0.85rem">🤖 选择分析模型：</span>
      <el-select v-model="selectedModel" placeholder="自动选择最佳模型" size="small" style="width:220px" @change="onModelChange">
        <el-option label="⭐ 最佳模型（自动）" value="" />
        <el-option v-for="m in modelList" :key="m.key" :label="`${m.name} (R²=${m.r2})`" :value="m.key" />
      </el-select>
    </div>
    <!-- 选中模型的特征重要性 -->
    <div v-if="modelFIOption" style="margin-bottom:16px">
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

    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="6" v-for="c in cards" :key="c.label">
        <el-card class="card-dark" shadow="hover">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value">{{ c.value }}</div>
        </el-card>
      </el-col>
    </el-row>
    <!-- 群体质量分布 -->
    <div style="margin-top:20px">
      <el-card class="card-dark" style="margin-bottom:20px">
        <template #header>
          <span>📊 全体用户睡眠质量分布</span>
          <span v-if="distStats" style="float:right;font-size:0.75rem;color:#889">
            均值 {{ distStats.avg }} | 范围 {{ distStats.min }}-{{ distStats.max }} | 共 {{ distStats.total }} 条
          </span>
        </template>
        <v-chart class="chart" :option="distOption" autoresize />
      </el-card>
      <el-card class="card-dark">
        <template #header>🍰 群体睡眠结构</template>
        <v-chart class="chart" :option="structOption" autoresize />
      </el-card>
    </div>
    <!-- 影响因素排行 -->
    <el-card class="card-dark" style="margin-top:20px">
      <template #header>📈 群体影响因素排行</template>
      <v-chart class="chart" :option="rankOption" autoresize />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { getAdminDashboard, getGroupQualityDist, getGroupSleepStructure, getGroupInfluenceRanking, getPublicModelComparison } from '../api/sleep'
import { formatMinutes } from '../utils/format'

use([CanvasRenderer,BarChart,PieChart,TitleComponent,TooltipComponent,LegendComponent,GridComponent])

const dash = reactive({
  total_users:0,total_records:0,total_reports:0,
  new_users_today:0,new_records_today:0,avg_quality_all_users:0,
  avg_steps:0,avg_sleep_hours:0,avg_heart_rate:0,
  avg_efficiency_pct:0,avg_deep_min:0,avg_rem_min:0,
})
const distOption = ref({})
const distStats = ref(null)
const structOption = ref({})
const rankOption = ref({})
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
}

// 根据数值映射到渐变色（用于分布柱状图）
function getQualityColor(score) {
  if (score >= 8) return '#67c23a'
  if (score >= 6) return '#409eff'
  if (score >= 4) return '#e6a23c'
  return '#f56c6c'
}

const cards = computed(() => [
  { label:'总用户数', value:dash.total_users },
  { label:'总数据条数', value:dash.total_records },
  { label:'总报告数', value:dash.total_reports },
  { label:'今日新增用户', value:dash.new_users_today },
  { label:'今日新增记录', value:dash.new_records_today },
  { label:'全体平均质量分', value:dash.avg_quality_all_users },
  { label:'平均步数', value:dash.avg_steps },
  { label:'平均睡眠时长', value:formatMinutes((dash.avg_sleep_hours||0)*60) },
  { label:'平均心率(bpm)', value:dash.avg_heart_rate },
  { label:'平均睡眠效率(%)', value:dash.avg_efficiency_pct },
  { label:'平均深睡', value:formatMinutes(dash.avg_deep_min) },
  { label:'平均REM', value:formatMinutes(dash.avg_rem_min) },
])

onMounted(async () => {
  try {
    const [d, dist, struct, rank] = await Promise.all([
      getAdminDashboard(), getGroupQualityDist(), getGroupSleepStructure(), getGroupInfluenceRanking()
    ])
    Object.assign(dash, d.data.stats)
    const dd=dist.data, ds=struct.data, dr=rank.data

    // 分布图：精细分箱 + 渐变色 + 分布曲线
    const ranges = dd.distribution.map(x=>x.range)
    const counts = dd.distribution.map(x=>x.count)
    distStats.value = { avg: dd.avg_quality, min: dd.min_quality, max: dd.max_quality, total: dd.total_records }
    const maxCount = Math.max(...counts, 1)
    distOption.value = {
      tooltip:{trigger:'axis',formatter:(p)=>{const r=p[0];return `<b>质量分 ${r.name}</b><br/>人数: ${r.value}`}},
      grid:{left:'8%',right:'5%',top:'5%',bottom:'10%'},
      xAxis:{type:'category',data:ranges,axisLabel:{color:'#889',rotate:45,fontSize:9},name:'睡眠质量分区间',nameTextStyle:{color:'#889'}},
      yAxis:{type:'value',axisLabel:{color:'#889'},name:'人数',nameTextStyle:{color:'#889'}},
      series:[{
        type:'bar',data:counts.map((c,i)=>{
          const midScore = 1 + i*0.5 + 0.25
          return {value:c,itemStyle:{color:getQualityColor(midScore),borderRadius:[4,4,0,0]}}
        }),
        barMaxWidth:40
      }]
    }

    structOption.value = { tooltip:{trigger:'item',formatter:(p)=>`${p.name}: ${formatMinutes(p.value)} (${p.percent}%)`}, legend:{bottom:0,textStyle:{color:'#aaa'}}, series:[{type:'pie',radius:['40%','70%'],label:{color:'#ccc'},data:ds.stages.map(s=>({name:s.name,value:s.value,itemStyle:{color:s.name==='深睡'?'#1a5276':s.name==='浅睡'?'#5dade2':s.name==='REM'?'#8e44ad':'#e74c3c'}}))}] }
    rankOption.value = { tooltip:{formatter:(p)=>`${p.name}: ${p.value}`}, grid:{left:'25%'}, xAxis:{type:'value',axisLabel:{color:'#889'}}, yAxis:{type:'category',data:dr.ranking.map(r=>r.label).reverse(),axisLabel:{color:'#889'}}, series:[{type:'bar',data:dr.ranking.map(r=>r.correlation).reverse(),itemStyle:{color:'#ffd04b'},label:{show:true,position:'right',formatter:'{c}'}}] }

    // 加载模型列表
    try {
      const mc = await getPublicModelComparison()
      if (mc.data?.model_comparison) {
        cachedModelData.value = mc.data
        const entries = Object.entries(mc.data.model_comparison)
          .filter(([,v]) => v && typeof v.r2 === 'number')
          .map(([key,val]) => ({key,name:val.name||key,r2:val.r2??0}))
          .sort((a,b)=>(b.r2||0)-(a.r2||0))
        modelList.value = entries
        // 默认展示最佳模型特征重要性
        onModelChange('')
      }
    } catch(_){}
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.chart { width:100%; height:400px; }
.card-dark .stat-label { font-size: 0.8rem; color: #8899aa; }
.card-dark .stat-value { font-size: 1.6rem; font-weight: 700; color: #ffd04b; margin-top: 4px; }
</style>
