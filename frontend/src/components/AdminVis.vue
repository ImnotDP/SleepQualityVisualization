<template>
  <div class="page">
    <h2 style="margin-bottom:20px">📈 群体可视化分析</h2>

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

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="🔥 全局相关性热力图" name="corr">
        <el-card class="card-dark"><v-chart class="chart" style="height:550px" :option="corrOption" autoresize /></el-card>
      </el-tab-pane>
      <el-tab-pane label="📊 群体睡眠时长分布" name="dist">
        <el-card class="card-dark"><v-chart class="chart" :option="distOption" autoresize /></el-card>
      </el-tab-pane>
      <el-tab-pane label="📈 群体睡眠质量趋势" name="trend">
        <el-card class="card-dark"><v-chart class="chart" :option="trendOption" autoresize /></el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, HeatmapChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import { getGlobalCorrelation, getGlobalDistribution, getPublicModelComparison } from '../api/sleep'

use([CanvasRenderer,LineChart,BarChart,PieChart,HeatmapChart,TitleComponent,TooltipComponent,LegendComponent,GridComponent,VisualMapComponent])

// 热力图颜色映射
const HEAT_COLORS = ['#313695','#4575b4','#74add1','#abd9e9','#fee090','#f46d43','#d73027','#a50026']

// 计算颜色的相对亮度（用于决定文字用黑色还是白色）
function getLuminance(hexColor) {
  const r = parseInt(hexColor.slice(1,3), 16) / 255
  const g = parseInt(hexColor.slice(3,5), 16) / 255
  const b = parseInt(hexColor.slice(5,7), 16) / 255
  // 相对亮度公式
  const linR = r <= 0.03928 ? r/12.92 : Math.pow((r+0.055)/1.055, 2.4)
  const linG = g <= 0.03928 ? g/12.92 : Math.pow((g+0.055)/1.055, 2.4)
  const linB = b <= 0.03928 ? b/12.92 : Math.pow((b+0.055)/1.055, 2.4)
  return 0.2126*linR + 0.7152*linG + 0.0722*linB
}

// 根据相关系数值插值背景色
function getBgColor(value, minVal, maxVal) {
  const t = (value - minVal) / (maxVal - minVal || 1)
  const idx = t * (HEAT_COLORS.length - 1)
  const i0 = Math.floor(idx)
  const i1 = Math.min(i0+1, HEAT_COLORS.length-1)
  const frac = idx - i0
  const c0 = HEAT_COLORS[i0], c1 = HEAT_COLORS[i1]
  const r = Math.round(parseInt(c0.slice(1,3),16)*(1-frac) + parseInt(c1.slice(1,3),16)*frac)
  const g = Math.round(parseInt(c0.slice(3,5),16)*(1-frac) + parseInt(c1.slice(3,5),16)*frac)
  const b = Math.round(parseInt(c0.slice(5,7),16)*(1-frac) + parseInt(c1.slice(5,7),16)*frac)
  return '#' + [r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('')
}

const activeTab = ref('corr')
const corrOption = ref({})
const distOption = ref({})
const trendOption = ref({})
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

onMounted(async () => {
  try {
    const [corr, dist] = await Promise.all([getGlobalCorrelation(), getGlobalDistribution()])
    const cd=corr.data, dd=dist.data

    const fields=cd.fields, labels=cd.field_labels||{}, mat=[]
    fields.forEach((f1,i)=>{ fields.forEach((f2,j)=>{ mat.push([j,i,cd.correlation_matrix[`${f1}|${f2}`]||0]) }) })
    const xLabels = fields.map(f=>labels[f]||f)
    corrOption.value = {
      tooltip:{
        formatter:(p)=>{
          const xl=xLabels[p.value[0]]||'';const yl=xLabels[p.value[1]]||''
          return `<b>X: ${xl}</b><br/><b>Y: ${yl}</b><br/>相关系数: ${p.value[2].toFixed(4)}`
        }
      },
      grid:{left:'18%',bottom:'12%',top:'2%',right:'5%'},
      xAxis:{type:'category',data:xLabels,axisLabel:{color:'#889',rotate:35,fontSize:9},position:'bottom',name:'特征',nameTextStyle:{color:'#889'}},
      yAxis:{type:'category',data:xLabels,axisLabel:{color:'#889',fontSize:9},name:'特征',nameTextStyle:{color:'#889'}},
      visualMap:{min:-1,max:1,calculable:true,orient:'horizontal',left:'center',bottom:0,inRange:{color:HEAT_COLORS}},
      series:[{
        type:'heatmap',data:mat,
        emphasis:{itemStyle:{shadowBlur:10,shadowColor:'rgba(0,0,0,0.5)'}},
      }]
    }

    // 时长分布直方图 - 精细分箱
    const durations=dd.sleep_durations||[]
    if(durations.length){
      const min=Math.floor(Math.min(...durations)),max=Math.ceil(Math.max(...durations))
      const binCount = Math.min(20, Math.max(8, Math.ceil((max-min)/15)))
      const step=Math.ceil((max-min)/binCount)||1
      const bins={}; durations.forEach(v=>{const k=Math.floor(v/step)*step; bins[k]=(bins[k]||0)+1})
      const keys=Object.keys(bins).map(Number).sort((a,b)=>a-b)
      const maxVal = Math.max(...Object.values(bins),1)
      distOption.value = {
        tooltip:{trigger:'axis',formatter:(p)=>{const r=p[0];return `<b>${r.name} 分钟</b><br/>天数: ${r.value}`}},
        grid:{left:'8%',right:'5%',top:'5%',bottom:'10%'},
        xAxis:{type:'category',data:keys.map(k=>`${k}-${k+step}`),axisLabel:{color:'#889',rotate:30,fontSize:9},name:'睡眠时长(分钟)',nameTextStyle:{color:'#889'}},
        yAxis:{type:'value',axisLabel:{color:'#889'},name:'天数',nameTextStyle:{color:'#889'}},
        series:[{type:'bar',data:keys.map(k=>({value:bins[k],itemStyle:{color:'#67c23a',borderRadius:[4,4,0,0]}})),barMaxWidth:40}]
      }
    }
    // 质量趋势
    const scores=dd.quality_scores||[]
    trendOption.value = {
      tooltip:{trigger:'axis',formatter:(p)=>{const r=p[0];return `<b>记录 #${r.name}</b><br/>质量分: ${r.value}`}},
      grid:{left:'8%',right:'5%',top:'5%',bottom:'10%'},
      xAxis:{type:'category',data:scores.map((_,i)=>i+1),axisLabel:{color:'#889'},name:'记录序号',nameTextStyle:{color:'#889'}},
      yAxis:{type:'value',axisLabel:{color:'#889'},name:'睡眠质量分',nameTextStyle:{color:'#889'},min:1,max:10},
      series:[{type:'line',smooth:true,data:scores,itemStyle:{color:'#ffd04b'},areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(255,208,75,0.3)'},{offset:1,color:'rgba(255,208,75,0)'}]}}}]
    }

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
  } catch(e){console.error(e)}
})
</script>

<style scoped>
.chart { width:100%; height:400px; }
</style>
