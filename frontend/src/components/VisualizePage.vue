<template>
  <div class="viz-page">
    <div class="page-hero">
      <h2 class="page-title">📊 可视化分析</h2>
      <p class="page-subtitle">您的个人睡眠数据多维度可视化分析</p>
    </div>

    <!-- ========== 趋势图 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'trend' }">
      <div class="section-header" @click="toggleFs('trend')">
        <span class="section-icon">📈</span>
        <span class="section-label">睡眠趋势总览</span>
        <span class="section-badge">质量分 · 效率 · 睡眠时长</span>
        <span class="section-fs-btn" :title="fsSection==='trend'?'退出全屏':'全屏查看'">{{ fsSection==='trend'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <v-chart class="chart chart-tall" :option="trendOption" autoresize />
      </div>
    </div>

    <!-- ========== 散点图 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'scatter' }">
      <div class="section-header" @click="toggleFs('scatter')">
        <span class="section-icon">🎯</span>
        <span class="section-label">指标关联散点图</span>
        <span class="section-badge">心率 · 步数 vs 睡眠质量</span>
        <span class="section-fs-btn" :title="fsSection==='scatter'?'退出全屏':'全屏查看'">{{ fsSection==='scatter'?'✕':'⛶'}}</span>
      </div>
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
    </div>

    <!-- ========== 直方图 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'histogram' }">
      <div class="section-header" @click="toggleFs('histogram')">
        <span class="section-icon">📊</span>
        <span class="section-label">数据分布直方图</span>
        <span class="section-badge">步数 · 睡眠时长分布</span>
        <span class="section-fs-btn" :title="fsSection==='histogram'?'退出全屏':'全屏查看'">{{ fsSection==='histogram'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <div class="chart-card">
              <div class="chart-card-title">🚶 日步数分布</div>
              <v-chart class="chart" :option="histStepsOption" autoresize />
            </div>
          </el-col>
          <el-col :xs="24" :sm="12">
            <div class="chart-card">
              <div class="chart-card-title">😴 睡眠时长分布</div>
              <v-chart class="chart" :option="histSleepOption" autoresize />
            </div>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- ========== 相关性热力图 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'correlation' }">
      <div class="section-header" @click="toggleFs('correlation')">
        <span class="section-icon">🔥</span>
        <span class="section-label">多维相关性热力图</span>
        <span class="section-badge">全维度特征关联矩阵（含环境参数）</span>
        <span class="section-fs-btn" :title="fsSection==='correlation'?'退出全屏':'全屏查看'">{{ fsSection==='correlation'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <div class="chart-card">
          <v-chart class="chart chart-xl" :option="corrOption" autoresize />
        </div>
      </div>
    </div>

    <!-- ========== 阶段占比 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'stage' }">
      <div class="section-header" @click="toggleFs('stage')">
        <span class="section-icon">🍰</span>
        <span class="section-label">睡眠阶段占比</span>
        <span class="section-badge">深睡 · 浅睡 · REM · 清醒</span>
        <span class="section-fs-btn" :title="fsSection==='stage'?'退出全屏':'全屏查看'">{{ fsSection==='stage'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <div class="chart-card">
          <v-chart class="chart" :option="pieOption" autoresize />
        </div>
      </div>
    </div>

    <!-- ========== 环境参数 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'environment' }">
      <div class="section-header" @click="toggleFs('environment')">
        <span class="section-icon">🌡️</span>
        <span class="section-label">环境参数影响分析</span>
        <span class="section-badge">温度 · 湿度 · 噪声 · 血氧 · 体动</span>
        <span class="section-fs-btn" :title="fsSection==='environment'?'退出全屏':'全屏查看'">{{ fsSection==='environment'?'✕':'⛶'}}</span>
      </div>
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
    </div>

    <!-- ========== 全模型对比 ========== -->
    <div class="viz-section" :class="{ 'viz-fullscreen': fsSection === 'models' }">
      <div class="section-header" @click="toggleFs('models')">
        <span class="section-icon">🤖</span>
        <span class="section-label">全模型算法对比</span>
        <span class="section-badge">12种回归算法 · R²/MAE/RMSE</span>
        <span class="section-fs-btn" :title="fsSection==='models'?'退出全屏':'全屏查看'">{{ fsSection==='models'?'✕':'⛶'}}</span>
      </div>
      <div class="section-body">
        <el-row :gutter="16">
          <el-col :xs="24" :lg="14">
            <div class="chart-card">
              <div class="chart-card-title">📊 各算法 R² 决定系数对比（越高越好）</div>
              <v-chart class="chart chart-tall" :option="modelR2Option" autoresize />
            </div>
          </el-col>
          <el-col :xs="24" :lg="10">
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
          </el-col>
        </el-row>
        <div class="chart-card" style="margin-top:8px">
          <div class="chart-card-title">📈 各算法 MAE / RMSE 误差对比（越低越好）</div>
          <v-chart class="chart chart-tall" :option="modelErrorOption" autoresize />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, ToolboxComponent, VisualMapComponent } from 'echarts/components'
import { getTrendData, getScatterData, getHistogramData, getCorrelationData, getStagePieData, getEnvironmentData, getEnvironmentVsQuality, getFeatureAnalysis } from '../api/sleep'

use([CanvasRenderer,LineChart,BarChart,PieChart,ScatterChart,HeatmapChart,TitleComponent,TooltipComponent,LegendComponent,GridComponent,ToolboxComponent,VisualMapComponent])

// 全屏切换
const fsSection = ref(null)
function toggleFs(name) {
  fsSection.value = fsSection.value === name ? null : name
}

// 图表 refs
const trendOption = ref({})
const scatterHROption = ref({})
const scatterStepsOption = ref({})
const histStepsOption = ref({})
const histSleepOption = ref({})
const corrOption = ref({})
const pieOption = ref({})
const envTempOption = ref({})
const envHumidOption = ref({})
const envNoiseOption = ref({})
const envSpo2Option = ref({})
const envTrendOption = ref({})

// 模型对比
const modelR2Option = ref({})
const modelErrorOption = ref({})
const modelTableData = ref([])

function buildHistogram(data) {
  if (!data.length) return {}
  const min=Math.floor(Math.min(...data)), max=Math.ceil(Math.max(...data))
  const step=Math.ceil((max-min)/15)||1
  const bins={}; data.forEach(v=>{const k=Math.floor(v/step)*step; bins[k]=(bins[k]||0)+1})
  const keys=Object.keys(bins).map(Number).sort((a,b)=>a-b)
  return { tooltip:{trigger:'axis'}, xAxis:{type:'category',data:keys.map(k=>`${k}-${k+step}`),axisLabel:{color:'#889'}}, yAxis:{type:'value',axisLabel:{color:'#889'}}, series:[{type:'bar',data:keys.map(k=>bins[k]),itemStyle:{color:'#409eff',borderRadius:[4,4,0,0]}}] }
}

onMounted(async () => {
  try {
    const [trend, scatter, hist, corr, pie, env, envVs] = await Promise.all([
      getTrendData(), getScatterData(), getHistogramData(), getCorrelationData(), getStagePieData(),
      getEnvironmentData(), getEnvironmentVsQuality()
    ])
    const t=trend.data, s=scatter.data, h=hist.data, c=corr.data, p=pie.data
    const ev=env.data, evv=envVs.data

    trendOption.value = {
      tooltip:{trigger:'axis'}, legend:{data:['质量分','效率%','睡眠(小时)'],textStyle:{color:'#aaa'},top:0},
      grid:{left:'3%',right:'5%',top:'12%',bottom:'5%'},
      xAxis:{type:'category',data:t.dates,axisLabel:{color:'#889',rotate:30,fontSize:10}},
      yAxis:[{type:'value',axisLabel:{color:'#889'}},{type:'value',axisLabel:{color:'#889'}}],
      series:[
        {name:'质量分',type:'line',smooth:true,data:t.quality_scores,symbol:'circle',symbolSize:4,itemStyle:{color:'#ffd04b'},lineStyle:{width:2.5}},
        {name:'效率%',type:'line',smooth:true,data:t.efficiency_pct,symbol:'diamond',symbolSize:4,itemStyle:{color:'#67c23a'},lineStyle:{width:2}},
        {name:'睡眠(小时)',type:'line',smooth:true,yAxisIndex:1,data:t.total_sleep_hours,symbol:'triangle',symbolSize:4,itemStyle:{color:'#409eff'},lineStyle:{width:2}},
      ]
    }
    const scOpt = (name, data, color) => ({
      tooltip:{}, grid:{left:'12%',right:'5%',top:'8%',bottom:'10%'},
      xAxis:{name,nameLocation:'center',nameGap:28,axisLabel:{color:'#889'}},
      yAxis:{name:'质量分',axisLabel:{color:'#889'}},
      series:[{type:'scatter',data,symbolSize:7,itemStyle:{color,opacity:0.7}}],
    })
    scatterHROption.value = scOpt('心率(bpm)', s.hr_vs_quality, '#ff6b6b')
    scatterStepsOption.value = scOpt('步数', s.steps_vs_quality, '#4ecdc4')
    histStepsOption.value = buildHistogram(h.steps_distribution)
    histSleepOption.value = buildHistogram(h.sleep_duration_distribution)

    const fields=c.fields, labels=c.field_labels, mat=[]
    fields.forEach((f1,i)=>{ fields.forEach((f2,j)=>{ mat.push([j,i,c.correlation_matrix[`${f1}|${f2}`]||0]) }) })
    corrOption.value = {
      tooltip:{}, grid:{left:'18%',bottom:'12%',top:'2%',right:'5%'},
      xAxis:{type:'category',data:fields.map(f=>labels[f]||f),axisLabel:{color:'#889',rotate:35,fontSize:9},position:'bottom'},
      yAxis:{type:'category',data:fields.map(f=>labels[f]||f),axisLabel:{color:'#889',fontSize:9}},
      visualMap:{min:-1,max:1,calculable:true,orient:'horizontal',left:'center',bottom:0,inRange:{color:['#313695','#4575b4','#74add1','#abd9e9','#fee090','#f46d43','#d73027','#a50026']}},
      series:[{type:'heatmap',data:mat,label:{show:true,fontSize:7,color:'#ccc'},emphasis:{itemStyle:{shadowBlur:10,shadowColor:'rgba(0,0,0,0.5)'}}}],
    }
    pieOption.value = {
      tooltip:{trigger:'item',formatter:'{b}: {c}分钟 ({d}%)'},
      legend:{bottom:0,textStyle:{color:'#aaa',fontSize:11}},
      series:[{type:'pie',radius:['45%','72%'],center:['50%','45%'],avoidLabelOverlap:false,itemStyle:{borderRadius:6,borderColor:'#1a2a3a',borderWidth:3},label:{show:true,position:'outside',color:'#ccc',formatter:'{b}\n{d}%'},emphasis:{label:{fontSize:18,fontWeight:'bold'}},data:p.stages.map(s=>({...s,itemStyle:{color:s.name==='深睡'?'#1a5276':s.name==='浅睡'?'#5dade2':s.name==='REM'?'#8e44ad':'#e74c3c'}}))}],
    }

    const makeScatter = (data, name) => ({
      tooltip:{}, grid:{left:'12%',right:'5%',top:'10%',bottom:'12%'},
      xAxis:{name,nameLocation:'center',nameGap:25,axisLabel:{color:'#889',fontSize:9}},
      yAxis:{name:'质量分',axisLabel:{color:'#889',fontSize:9}},
      series:[{type:'scatter',data,symbolSize:5,itemStyle:{color:'#409eff',opacity:0.6}}],
    })
    if (evv?.scatter_data) {
      envTempOption.value = makeScatter(evv.scatter_data.temperature||[], '温度(°C)')
      envHumidOption.value = makeScatter(evv.scatter_data.humidity||[], '湿度(%)')
      envNoiseOption.value = makeScatter(evv.scatter_data.noise_db||[], '噪声(dB)')
      envSpo2Option.value = makeScatter(evv.scatter_data.spo2||[], '血氧(%)')
    }
    if (ev?.dates) {
      envTrendOption.value = {
        tooltip:{trigger:'axis'}, legend:{data:['温度°C','湿度%','噪声dB','血氧%','体动'],textStyle:{color:'#aaa'},top:0},
        grid:{left:'5%',right:'5%',top:'12%',bottom:'8%'},
        xAxis:{type:'category',data:ev.dates,axisLabel:{color:'#889',rotate:30,fontSize:9}},
        yAxis:[{type:'value',name:'温度/湿度/血氧',axisLabel:{color:'#889',fontSize:9}},{type:'value',name:'噪声dB',axisLabel:{color:'#889',fontSize:9}}],
        series:[
          {name:'温度°C',type:'line',smooth:true,data:ev.temperature,symbol:'none',itemStyle:{color:'#e74c3c'},lineStyle:{width:2}},
          {name:'湿度%',type:'line',smooth:true,data:ev.humidity,symbol:'none',itemStyle:{color:'#3498db'},lineStyle:{width:2}},
          {name:'血氧%',type:'line',smooth:true,data:ev.spo2,symbol:'none',itemStyle:{color:'#2ecc71'},lineStyle:{width:2}},
          {name:'噪声dB',type:'line',smooth:true,yAxisIndex:1,data:ev.noise_db,symbol:'none',itemStyle:{color:'#f39c12'},lineStyle:{width:1.5,type:'dashed'}},
          {name:'体动',type:'line',smooth:true,data:ev.movement_freq,symbol:'none',itemStyle:{color:'#9b59b6'},lineStyle:{width:1.5,type:'dashed'}},
        ]
      }
    }
  } catch (e) { console.error(e) }

  // 加载全模型对比数据
  try {
    const fa = await getFeatureAnalysis()
    const mc = fa.data?.model_comparison
    if (mc) {
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

      // R² 横向柱状图
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

      // MAE / RMSE 双柱状图
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
  } catch (e) { console.error('模型对比加载失败:', e) }
})
</script>

<style scoped>
.viz-page { padding: 4px; max-width: 1400px; margin: 0 auto; }
.page-hero { text-align: center; padding: 16px 0 24px; background: linear-gradient(180deg, rgba(26,42,58,0.4) 0%, transparent 100%); border-radius: 12px; margin-bottom: 8px; }
.page-title { font-size: 1.8rem; font-weight: 700; color: #ffd04b; margin: 0 0 6px; letter-spacing: 1px; }
.page-subtitle { color: #7a8a9a; font-size: 0.9rem; margin: 0; }

/* ====== 可视化区块（替代 collapse） ====== */
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
.viz-fullscreen .chart-sm { height: 350px !important; }

.chart-card { background: #162230; border: 1px solid #243444; border-radius: 10px; padding: 12px; margin-bottom: 8px; transition: border-color 0.2s; }
.chart-card:hover { border-color: #3a5a7a; }
.chart-card-title { color: #8899aa; font-size: 0.8rem; font-weight: 600; margin-bottom: 8px; padding-left: 4px; letter-spacing: 0.5px; }

.chart { width: 100%; height: 380px; }
.chart-sm { height: 280px; }
.chart-tall { height: 450px; }
.chart-xl { height: 550px; }

@media (max-width: 767px) {
  .section-badge { display: none; }
  .chart { height: 300px; } .chart-sm { height: 240px; } .chart-tall { height: 340px; } .chart-xl { height: 400px; }
  .page-title { font-size: 1.3rem; }
}
</style>
