<template>
  <div class="page">
    <h2 style="margin-bottom:20px">👤 个人中心</h2>
    <el-row :gutter="20">
      <el-col :xs="24" :md="12">
        <el-card class="card-dark">
          <template #header>📋 历史预测报告</template>
          <el-table :data="reports" stripe max-height="400" v-loading="loading" empty-text="暂无预测报告">
            <el-table-column prop="created_at" label="时间" width="180" />
            <el-table-column prop="predicted_score" label="预测分数" width="100">
              <template #default="{ row }"><el-tag :type="row.predicted_score>=80?'success':row.predicted_score>=60?'warning':'danger'">{{ row.predicted_score }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="suggestions" label="建议" show-overflow-tooltip />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button text type="primary" @click="showDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination v-model:current-page="page" :page-size="20" :total="total" small layout="prev,pager,next" @current-change="fetchReports" style="margin-top:10px" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card class="card-dark" v-if="detailReport">
          <template #header>📄 报告详情</template>
          <div v-if="detailReport">
            <p><strong>预测分数：</strong><el-tag :type="detailReport.predicted_score>=80?'success':'warning'">{{ detailReport.predicted_score }}</el-tag></p>
            <p style="margin-top:10px"><strong>输入参数：</strong></p>
            <el-table :data="paramRows" size="small" stripe max-height="300">
              <el-table-column prop="label" label="指标" />
              <el-table-column prop="value" label="值" />
            </el-table>
            <p style="margin-top:10px"><strong>特征重要性：</strong></p>
            <el-table :data="impRows" size="small" stripe max-height="300">
              <el-table-column prop="label" label="特征" />
              <el-table-column prop="importance" label="权重" />
              <el-table-column prop="direction" label="方向" />
            </el-table>
            <p style="margin-top:10px"><strong>建议：</strong></p>
            <el-alert :title="detailReport.suggestions" type="info" :closable="false" style="white-space:pre-wrap" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getReports, getReportDetail } from '../api/sleep'

const loading = ref(false)
const reports = ref([])
const page = ref(1)
const total = ref(0)
const detailReport = ref(null)

const paramRows = computed(() => {
  if (!detailReport.value?.input_params) return []
  const labels = { totalSleepMinutes:'总睡眠时长', deepSleepTime:'深睡时长', REMTime:'REM时长',
    sleepEfficiency:'睡眠效率', daySteps:'步数', avgHeartRate:'平均心率' }
  return Object.entries(detailReport.value.input_params).map(([k,v])=>({label:labels[k]||k,value:v}))
})
const impRows = computed(() => {
  if (!detailReport.value?.feature_importance) return []
  const labels = { totalSleepMinutes:'总睡眠时长', deepSleepTime:'深睡时长', REMTime:'REM时长',
    sleepEfficiency:'睡眠效率', daySteps:'步数', avgHeartRate:'平均心率' }
  return Object.entries(detailReport.value.feature_importance).map(([k,v])=>({label:labels[k]||k,importance:v,direction:v>0?'正向':'负向'}))
})

async function fetchReports(p=1) { page.value=p; loading.value=true; try { const r=await getReports(p,20); reports.value=r.data.data; total.value=r.data.total } catch(e){} finally{loading.value=false} }
async function showDetail(row) { try { const r=await getReportDetail(row.id); detailReport.value=r.data.data } catch(e){} }
onMounted(()=>fetchReports())
</script>
