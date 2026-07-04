<template>
  <div class="page">
    <h2 style="margin-bottom:20px">🔮 睡眠质量预测</h2>
    <el-row :gutter="20">
      <!-- 预测输入 -->
      <el-col :xs="24" :md="12">
        <el-card class="card-dark">
          <template #header>📝 输入参数（留空则使用历史均值）</template>
          <el-form :model="form" label-width="130px" size="small">
            <el-form-item v-for="f in fields" :key="f.key" :label="f.label">
              <el-input-number v-model="form[f.key]" :min="0" :step="f.step" style="width:100%" controls-position="right" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doPredict" :loading="predicting">🔮 预测睡眠质量</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      <!-- 预测结果 -->
      <el-col :xs="24" :md="12">
        <el-card class="card-dark" v-if="result">
          <template #header>📊 预测结果</template>
          <div style="text-align:center;margin-bottom:20px">
            <div class="stat-label">睡眠质量评分（1-10分制）</div>
            <div class="stat-value" style="font-size:3rem" :style="{color: result.rating_color||'#409eff'}">{{ result.predicted_score }}</div>
            <el-tag :type="ratingType" size="large" style="margin-top:8px">{{ result.rating }}</el-tag>
          </div>
          <!-- 评分明细 -->
          <div v-if="result.score_breakdown" style="margin-bottom:16px">
            <h4>📋 评分明细</h4>
            <el-row :gutter="12">
              <el-col :span="12" v-for="(v,k) in result.score_breakdown" :key="k">
                <div class="stat-label" style="font-size:12px">{{ {deep_sleep_quality:'深睡质量',rem_quality:'REM质量',efficiency_quality:'效率质量',continuity_quality:'连续性'}[k]||k }}</div>
                <el-progress :percentage="v*10" :color="v>7?'#67c23a':v>5?'#409eff':'#e6a23c'" />
              </el-col>
            </el-row>
          </div>
          <!-- 各模型预测结果 -->
          <div v-if="result.all_predictions" style="margin-bottom:16px">
            <h4>🔢 各模型预测分数对比</h4>
            <v-chart class="chart" :option="predChartOption" autoresize />
            <el-table :data="predictionList" size="small" stripe max-height="350" style="margin-top:8px">
              <el-table-column prop="name" label="算法模型" width="200" />
              <el-table-column prop="score" label="预测分数" width="120" sortable>
                <template #default="{row}">
                  <span :style="{color:row.score>=7?'#67c23a':row.score>=5?'#409eff':'#e6a23c',fontWeight:row.isBest?'bold':'normal',fontSize:row.isBest?'1.1em':'1em'}">
                    {{ row.score }} {{ row.isBest ? '⭐' : '' }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 模型对比 - 全算法表格 -->
          <div v-if="result.model_comparison" style="margin-bottom:16px">
            <h4>🤖 全模型对比 (R²)</h4>
            <el-table :data="modelCompareList" size="small" stripe max-height="350" style="margin-top:8px">
              <el-table-column prop="name" label="算法模型" width="200" />
              <el-table-column prop="r2" label="R²" sortable width="90">
                <template #default="{row}">
                  <span :style="{color:row.r2>0.6?'#67c23a':row.r2>0.3?'#409eff':'#e6a23c',fontWeight:row.key===result.best_model?'bold':'normal'}">{{ row.r2 }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="mae" label="MAE" sortable width="90" />
              <el-table-column prop="rmse" label="RMSE" sortable width="90" />
              <el-table-column label="评级" width="80">
                <template #default="{row}">
                  <el-tag :type="row.r2>0.6?'success':row.r2>0.3?'primary':'warning'" size="small">{{ row.r2>0.6?'优':row.r2>0.3?'中':'弱' }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
            <div style="text-align:right;font-size:11px;color:#999;margin-top:4px">
              最佳模型：<strong style="color:#67c23a">{{ result.best_model_name || result.best_model }}</strong>
              <span v-if="result.suggestions_source" style="margin-left:10px">建议来源：<el-tag size="small" :type="result.suggestions_source==='deepseek'?'success':'info'">{{ result.suggestions_source==='deepseek'?'DeepSeek AI':'规则引擎' }}</el-tag></span>
            </div>
          </div>
          <el-divider />
          <h4>特征重要性排行</h4>
          <el-table :data="impList" size="small" stripe max-height="300">
            <el-table-column prop="label" label="特征" />
            <el-table-column prop="importance" label="权重" sortable />
            <el-table-column prop="direction" label="方向" width="70">
              <template #default="{ row }"><el-tag :type="row.direction==='正向'?'success':'danger'" size="small">{{ row.direction }}</el-tag></template>
            </el-table-column>
          </el-table>
          <el-divider />
          <h4>💡 个性化建议</h4>
          <el-alert :title="result.suggestions" type="info" :closable="false" style="white-space:pre-wrap;margin-top:10px" />
        </el-card>
        <el-empty v-else description="输入参数后点击预测" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components'
import { predictScore } from '../api/sleep'
import { ElMessage } from 'element-plus'

use([CanvasRenderer, BarChart, TitleComponent, TooltipComponent, GridComponent])

const fields = [
  { key:'totalSleepMinutes', label:'总睡眠时长', step:10 },
  { key:'deepSleepTime', label:'深睡时长', step:5 },
  { key:'shallowSleepTime', label:'浅睡时长', step:5 },
  { key:'REMTime', label:'REM时长', step:5 },
  { key:'wakeTime', label:'清醒时长', step:5 },
  { key:'sleepEfficiency', label:'睡眠效率(0-1)', step:0.05 },
  { key:'deepSleepRatio', label:'深睡比例(0-1)', step:0.05 },
  { key:'REMRatio', label:'REM比例(0-1)', step:0.05 },
  { key:'daySteps', label:'日步数', step:500 },
  { key:'dayCalories', label:'日卡路里', step:50 },
  { key:'avgHeartRate', label:'平均心率(bpm)', step:1 },
  { key:'temperature', label:'环境温度(°C)', step:0.5 },
  { key:'humidity', label:'环境湿度(%)', step:1 },
  { key:'noise_db', label:'噪声分贝(dB)', step:1 },
  { key:'spo2', label:'血氧饱和度(%)', step:0.5 },
  { key:'movement_freq', label:'体动频率(次/分钟)', step:1 },
]

const form = reactive(Object.fromEntries(fields.map(f=>[f.key,null])))
const predicting = ref(false)
const result = ref(null)

const impList = computed(() => {
  if (!result.value?.feature_importance) return []
  const labels = Object.fromEntries(fields.map(f=>[f.key,f.label]))
  return Object.entries(result.value.feature_importance).map(([k,v])=>({label:labels[k]||k,importance:v,direction:v>0?'正向':'负向'}))
})

const modelCompareList = computed(() => {
  if (!result.value?.model_comparison) return []
  return Object.entries(result.value.model_comparison)
    .filter(([k,v]) => v && typeof v.r2 === 'number')
    .map(([key, val]) => ({
      key,
      name: val.name || key,
      r2: val.r2,
      mae: val.mae,
      rmse: val.rmse,
    }))
    .sort((a, b) => (b.r2 || 0) - (a.r2 || 0))
})

const algoNames = {
  svr:'支持向量回归(SVR)',linear:'线性回归(Linear)',rf:'随机森林(RF)',
  gradient_boosting:'梯度提升(GBRT)',xgboost:'XGBoost',decision_tree:'决策树(DT)',
  ridge:'岭回归(Ridge)',lasso:'套索回归(Lasso)',elastic_net:'弹性网络(ElasticNet)',
  knn:'K近邻回归(KNN)',bayesian_ridge:'贝叶斯岭回归(BayesianRidge)',adaboost:'自适应增强(AdaBoost)',
}

const predictionList = computed(() => {
  if (!result.value?.all_predictions) return []
  const best = result.value.best_model
  return Object.entries(result.value.all_predictions)
    .map(([key, score]) => ({
      key,
      name: algoNames[key] || key,
      score,
      isBest: key === best,
    }))
    .sort((a, b) => b.score - a.score)
})

const predChartOption = computed(() => {
  const list = predictionList.value
  if (!list.length) return {}
  const names = list.map(e => e.name)
  const scores = list.map(e => e.score)
  const colors = scores.map(s => s >= 7 ? '#67c23a' : s >= 5 ? '#409eff' : '#e6a23c')
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '8%', top: '5%', bottom: '8%', containLabel: true },
    xAxis: { type: 'value', name: '预测分数', max: 10, axisLabel: { color: '#889' } },
    yAxis: { type: 'category', data: names.reverse(), axisLabel: { color: '#ccc', fontSize: 11 }, inverse: true },
    series: [{
      type: 'bar', data: scores.reverse().map((v, i) => ({
        value: v,
        itemStyle: { color: colors.reverse()[i], borderRadius: [0, 4, 4, 0] }
      })),
      label: { show: true, position: 'right', color: '#aaa', fontSize: 10, formatter: '{c}' },
      barMaxWidth: 28,
    }],
  }
})

const ratingType = computed(() => {
  const r = result.value?.rating
  if (r==='优秀') return 'success'
  if (r==='良好') return 'primary'
  if (r==='一般') return 'warning'
  return 'danger'
})

async function doPredict() {
  predicting.value = true
  try {
    const r = await predictScore(form)
    result.value = r.data
    ElMessage.success(`预测分数：${r.data.predicted_score}`)
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '预测失败')
  } finally { predicting.value = false }
}
</script>

<style scoped>
.best-model { border:2px solid #67c23a; }
.chart { width: 100%; height: 350px; }
</style>
