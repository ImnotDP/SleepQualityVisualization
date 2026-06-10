<template>
  <div class="page">
    <h2 style="margin-bottom:20px">📈 群体可视化分析</h2>
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
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import { getGlobalCorrelation, getGlobalDistribution } from '../api/sleep'

use([CanvasRenderer,LineChart,BarChart,PieChart,TitleComponent,TooltipComponent,LegendComponent,GridComponent,VisualMapComponent])

const activeTab = ref('corr')
const corrOption = ref({})
const distOption = ref({})
const trendOption = ref({})

onMounted(async () => {
  try {
    const [corr, dist] = await Promise.all([getGlobalCorrelation(), getGlobalDistribution()])
    const cd=corr.data, dd=dist.data

    // 热力图
    const fields=cd.fields, mat=[]
    fields.forEach((f1,i)=>{ fields.forEach((f2,j)=>{ mat.push([j,i,cd.correlation_matrix[`${f1}|${f2}`]||0]) }) })
    corrOption.value = {
      tooltip:{}, grid:{left:'15%',bottom:'15%'},
      xAxis:{type:'category',data:fields,axisLabel:{color:'#889',rotate:30,fontSize:10}},
      yAxis:{type:'category',data:fields,axisLabel:{color:'#889',fontSize:10}},
      visualMap:{min:-1,max:1,calculable:true,orient:'horizontal',left:'center',bottom:0,inRange:{color:['#313695','#4575b4','#74add1','#abd9e9','#fee090','#f46d43','#d73027','#a50026']}},
      series:[{type:'heatmap',data:mat,label:{show:true,fontSize:8}}]
    }
    // 时长分布直方图
    const durations=dd.sleep_durations||[]
    if(durations.length){
      const min=Math.floor(Math.min(...durations)),max=Math.ceil(Math.max(...durations)),step=Math.ceil((max-min)/15)||1
      const bins={}; durations.forEach(v=>{const k=Math.floor(v/step)*step; bins[k]=(bins[k]||0)+1})
      const keys=Object.keys(bins).map(Number).sort((a,b)=>a-b)
      distOption.value = { tooltip:{trigger:'axis'}, xAxis:{type:'category',data:keys.map(k=>`${k}-${k+step}`),axisLabel:{color:'#889'}}, yAxis:{type:'value',axisLabel:{color:'#889'}}, series:[{type:'bar',data:keys.map(k=>bins[k]),itemStyle:{color:'#67c23a'}}] }
    }
    // 质量趋势（简化：按记录数）
    const scores=dd.quality_scores||[]
    trendOption.value = { tooltip:{trigger:'axis'}, xAxis:{type:'category',data:scores.map((_,i)=>i+1),axisLabel:{color:'#889'}}, yAxis:{type:'value',axisLabel:{color:'#889'}}, series:[{type:'line',smooth:true,data:scores,itemStyle:{color:'#ffd04b'}}] }
  } catch(e){console.error(e)}
})
</script>

<style scoped>
.chart { width:100%; height:400px; }
</style>
