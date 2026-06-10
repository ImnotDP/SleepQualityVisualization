<template>
  <div class="page">
    <h2 style="margin-bottom:20px">🛡️ 管理员首页</h2>
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="6" v-for="c in cards" :key="c.label">
        <el-card class="card-dark" shadow="hover">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value">{{ c.value }}</div>
        </el-card>
      </el-col>
    </el-row>
    <!-- 群体质量分布 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :xs="24" :md="12">
        <el-card class="card-dark">
          <template #header>📊 全体用户睡眠质量分布</template>
          <v-chart class="chart" :option="distOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card class="card-dark">
          <template #header>🍰 群体睡眠结构</template>
          <v-chart class="chart" :option="structOption" autoresize />
        </el-card>
      </el-col>
    </el-row>
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
import { getAdminDashboard, getGroupQualityDist, getGroupSleepStructure, getGroupInfluenceRanking } from '../api/sleep'

use([CanvasRenderer,BarChart,PieChart,TitleComponent,TooltipComponent,LegendComponent,GridComponent])

const dash = reactive({ total_users:0,total_records:0,total_reports:0,new_users_today:0,new_records_today:0,avg_quality_all_users:0 })
const distOption = ref({})
const structOption = ref({})
const rankOption = ref({})

const cards = computed(() => [
  { label:'总用户数', value:dash.total_users },
  { label:'总数据条数', value:dash.total_records },
  { label:'今日新增用户', value:dash.new_users_today },
  { label:'全体平均质量分', value:dash.avg_quality_all_users },
])

onMounted(async () => {
  try {
    const [d, dist, struct, rank] = await Promise.all([
      getAdminDashboard(), getGroupQualityDist(), getGroupSleepStructure(), getGroupInfluenceRanking()
    ])
    Object.assign(dash, d.data.stats)
    const dd=dist.data, ds=struct.data, dr=rank.data
    distOption.value = { tooltip:{}, xAxis:{type:'category',data:dd.distribution.map(x=>x.range),axisLabel:{color:'#889'}}, yAxis:{type:'value',axisLabel:{color:'#889'}}, series:[{type:'bar',data:dd.distribution.map(x=>x.count),itemStyle:{color:'#409eff'}}] }
    structOption.value = { tooltip:{trigger:'item'}, legend:{bottom:0,textStyle:{color:'#aaa'}}, series:[{type:'pie',radius:['40%','70%'],label:{color:'#ccc'},data:ds.stages.map(s=>({name:s.name,value:s.value}))}] }
    rankOption.value = { tooltip:{}, grid:{left:'25%'}, xAxis:{type:'value',axisLabel:{color:'#889'}}, yAxis:{type:'category',data:dr.ranking.map(r=>r.label).reverse(),axisLabel:{color:'#889'}}, series:[{type:'bar',data:dr.ranking.map(r=>r.correlation).reverse(),itemStyle:{color:'#ffd04b'},label:{show:true,position:'right'}}] }
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.chart { width:100%; height:400px; }
</style>
