<template>
  <div class="page">
    <h2 style="margin-bottom:20px">📊 可视化分析</h2>
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="📈 趋势图" name="trend">
        <el-card class="card-dark"><v-chart class="chart" :option="trendOption" autoresize /></el-card>
      </el-tab-pane>
      <el-tab-pane label="🎯 散点图" name="scatter">
        <el-row :gutter="20">
          <el-col :xs="24" :md="12"><el-card class="card-dark"><template #header>心率 vs 睡眠质量</template><v-chart class="chart" :option="scatterHROption" autoresize /></el-card></el-col>
          <el-col :xs="24" :md="12"><el-card class="card-dark"><template #header>步数 vs 睡眠质量</template><v-chart class="chart" :option="scatterStepsOption" autoresize /></el-card></el-col>
        </el-row>
      </el-tab-pane>
      <el-tab-pane label="📊 直方图" name="histogram">
        <el-row :gutter="20">
          <el-col :xs="24" :md="12"><el-card class="card-dark"><template #header>步数分布</template><v-chart class="chart" :option="histStepsOption" autoresize /></el-card></el-col>
          <el-col :xs="24" :md="12"><el-card class="card-dark"><template #header>睡眠时长分布</template><v-chart class="chart" :option="histSleepOption" autoresize /></el-card></el-col>
        </el-row>
      </el-tab-pane>
      <el-tab-pane label="🔥 相关性热力图" name="correlation">
        <el-card class="card-dark"><v-chart class="chart" style="height:550px" :option="corrOption" autoresize /></el-card>
      </el-tab-pane>
      <el-tab-pane label="🍰 阶段占比" name="stage">
        <el-card class="card-dark"><v-chart class="chart" :option="pieOption" autoresize /></el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, ScatterChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, ToolboxComponent, VisualMapComponent } from 'echarts/components'
import { getTrendData, getScatterData, getHistogramData, getCorrelationData, getStagePieData } from '../api/sleep'

use([CanvasRenderer,LineChart,BarChart,PieChart,ScatterChart,TitleComponent,TooltipComponent,LegendComponent,GridComponent,ToolboxComponent,VisualMapComponent])

const activeTab = ref('trend')
const trendOption = ref({})
const scatterHROption = ref({})
const scatterStepsOption = ref({})
const histStepsOption = ref({})
const histSleepOption = ref({})
const corrOption = ref({})
const pieOption = ref({})

function buildHistogram(data, name) {
  if (!data.length) return {}
  const min=Math.floor(Math.min(...data)), max=Math.ceil(Math.max(...data))
  const step=Math.ceil((max-min)/15)||1
  const bins={}; data.forEach(v=>{const k=Math.floor(v/step)*step; bins[k]=(bins[k]||0)+1})
  const keys=Object.keys(bins).map(Number).sort((a,b)=>a-b)
  return { tooltip:{trigger:'axis'}, xAxis:{type:'category',data:keys.map(k=>`${k}-${k+step}`),axisLabel:{color:'#889'}}, yAxis:{type:'value',axisLabel:{color:'#889'}}, series:[{type:'bar',data:keys.map(k=>bins[k]),itemStyle:{color:'#409eff'}}] }
}

onMounted(async () => {
  try {
    const [trend, scatter, hist, corr, pie] = await Promise.all([
      getTrendData(), getScatterData(), getHistogramData(), getCorrelationData(), getStagePieData()
    ])
    const t=trend.data, s=scatter.data, h=hist.data, c=corr.data, p=pie.data
    trendOption.value = {
      tooltip:{trigger:'axis'}, legend:{data:['质量分','效率%','睡眠(小时)'],textStyle:{color:'#aaa'}},
      xAxis:{type:'category',data:t.dates,axisLabel:{color:'#889'}},
      yAxis:[{type:'value',axisLabel:{color:'#889'}},{type:'value',axisLabel:{color:'#889'}}],
      series:[
        {name:'质量分',type:'line',smooth:true,data:t.quality_scores,itemStyle:{color:'#ffd04b'}},
        {name:'效率%',type:'line',smooth:true,data:t.efficiency_pct,itemStyle:{color:'#67c23a'}},
        {name:'睡眠(小时)',type:'line',smooth:true,yAxisIndex:1,data:t.total_sleep_hours,itemStyle:{color:'#409eff'}},
      ]
    }
    scatterHROption.value = { tooltip:{}, xAxis:{name:'心率',axisLabel:{color:'#889'}}, yAxis:{name:'质量分',axisLabel:{color:'#889'}}, series:[{type:'scatter',data:s.hr_vs_quality,itemStyle:{color:'#ff6b6b'}}] }
    scatterStepsOption.value = { tooltip:{}, xAxis:{name:'步数',axisLabel:{color:'#889'}}, yAxis:{name:'质量分',axisLabel:{color:'#889'}}, series:[{type:'scatter',data:s.steps_vs_quality,itemStyle:{color:'#4ecdc4'}}] }
    histStepsOption.value = buildHistogram(h.steps_distribution, '步数')
    histSleepOption.value = buildHistogram(h.sleep_duration_distribution, '睡眠时长')
    const fields=c.fields, labels=c.field_labels, mat=[]
    fields.forEach((f1,i)=>{ fields.forEach((f2,j)=>{ mat.push([j,i,c.correlation_matrix[`${f1}|${f2}`]||0]) }) })
    corrOption.value = {
      tooltip:{}, grid:{left:'15%',bottom:'15%'},
      xAxis:{type:'category',data:fields.map(f=>labels[f]||f),axisLabel:{color:'#889',rotate:30,fontSize:10}},
      yAxis:{type:'category',data:fields.map(f=>labels[f]||f),axisLabel:{color:'#889',fontSize:10}},
      visualMap:{min:-1,max:1,calculable:true,orient:'horizontal',left:'center',bottom:0,inRange:{color:['#313695','#4575b4','#74add1','#abd9e9','#fee090','#f46d43','#d73027','#a50026']}},
      series:[{type:'heatmap',data:mat,label:{show:true,fontSize:8}}]
    }
    pieOption.value = { tooltip:{trigger:'item'}, legend:{bottom:0,textStyle:{color:'#aaa'}}, series:[{type:'pie',radius:['40%','70%'],center:['50%','45%'],label:{color:'#ccc'},data:p.stages.map(s=>({...s,itemStyle:{color:s.name==='深睡'?'#1a5276':s.name==='浅睡'?'#5dade2':s.name==='REM'?'#8e44ad':'#e74c3c'}}))}] }
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.chart { width:100%; height:400px; }
</style>
