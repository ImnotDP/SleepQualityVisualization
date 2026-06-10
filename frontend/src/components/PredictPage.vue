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
            <div class="stat-label">预测睡眠质量分</div>
            <div class="stat-value" style="font-size:3rem">{{ result.predicted_score }}</div>
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
import { predictScore } from '../api/sleep'
import { ElMessage } from 'element-plus'

const fields = [
  { key:'totalSleepMinutes', label:'总睡眠时长(分钟)', step:10 },
  { key:'deepSleepTime', label:'深睡时长(分钟)', step:5 },
  { key:'shallowSleepTime', label:'浅睡时长(分钟)', step:5 },
  { key:'REMTime', label:'REM时长(分钟)', step:5 },
  { key:'wakeTime', label:'清醒时长(分钟)', step:5 },
  { key:'sleepEfficiency', label:'睡眠效率(0-1)', step:0.05 },
  { key:'deepSleepRatio', label:'深睡比例(0-1)', step:0.05 },
  { key:'REMRatio', label:'REM比例(0-1)', step:0.05 },
  { key:'daySteps', label:'日步数', step:500 },
  { key:'dayCalories', label:'日卡路里', step:50 },
  { key:'avgHeartRate', label:'平均心率', step:1 },
]

const form = reactive(Object.fromEntries(fields.map(f=>[f.key,null])))
const predicting = ref(false)
const result = ref(null)

const impList = computed(() => {
  if (!result.value?.feature_importance) return []
  const labels = Object.fromEntries(fields.map(f=>[f.key,f.label]))
  return Object.entries(result.value.feature_importance).map(([k,v])=>({label:labels[k]||k,importance:v,direction:v>0?'正向':'负向'}))
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
