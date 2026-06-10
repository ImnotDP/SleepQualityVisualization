<template>
  <div class="page">
    <h2 style="margin-bottom:20px">🏠 个人首页</h2>
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="6" v-for="c in cards" :key="c.label">
        <el-card class="card-dark" shadow="hover">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value">{{ c.value }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card class="card-dark" style="margin-top:20px">
      <template #header>📋 最近睡眠记录</template>
      <el-table :data="records" stripe max-height="400" v-loading="loading" empty-text="暂无数据">
        <el-table-column prop="record_date" label="日期" width="120" sortable />
        <el-table-column prop="sleepQualityScore" label="睡眠质量分" width="120" sortable>
          <template #default="{ row }"><el-tag :type="tagType(row.sleepQualityScore)">{{ row.sleepQualityScore }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="totalSleepMinutes" label="总睡眠(分钟)" width="130" />
        <el-table-column prop="deepSleepTime" label="深睡" width="90" />
        <el-table-column prop="REMTime" label="REM" width="90" />
        <el-table-column prop="sleepEfficiency" label="效率" width="90">
          <template #default="{ row }">{{ (row.sleepEfficiency*100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column prop="daySteps" label="步数" width="90" />
        <el-table-column prop="avgHeartRate" label="心率" width="90" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getPersonalStats, getRecords } from '../api/sleep'

const loading = ref(false)
const records = ref([])
const stats = reactive({ total_records: 0, avg_quality_score: 0, avg_sleep_minutes: 0, avg_efficiency: 0, date_range_start: '', date_range_end: '' })

const cards = [
  { label: '记录条数', value: stats.total_records },
  { label: '平均质量分', value: stats.avg_quality_score },
  { label: '平均睡眠(分钟)', value: stats.avg_sleep_minutes },
  { label: '平均效率', value: (stats.avg_efficiency*100).toFixed(1)+'%' },
].map(c => ({ ...c, get value() { return c._get() }, _get() { return c._val }, set _val(v) { c._val = v } }))

function tagType(s) { return s>=80?'success':s>=60?'warning':'danger' }

onMounted(async () => {
  loading.value = true
  try {
    const [sRes, rRes] = await Promise.all([getPersonalStats(), getRecords(1, 5)])
    Object.assign(stats, sRes.data.stats || {})
    records.value = rRes.data.data || []
    // update card values
    cards[0]._val = stats.total_records
    cards[1]._val = stats.avg_quality_score
    cards[2]._val = stats.avg_sleep_minutes
    cards[3]._val = (stats.avg_efficiency*100).toFixed(1)+'%'
  } catch (e) { console.error(e) }
  finally { loading.value = false }
})
</script>
