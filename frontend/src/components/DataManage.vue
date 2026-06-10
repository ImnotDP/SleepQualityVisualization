<template>
  <div class="page">
    <h2 style="margin-bottom:20px">📁 数据管理</h2>
    <!-- 上传区域 -->
    <el-card class="card-dark" style="margin-bottom:20px">
      <template #header>📤 上传睡眠数据 (CSV)</template>
      <el-upload drag :auto-upload="false" :on-change="onFileChange" :limit="1" accept=".csv">
        <el-icon style="font-size:48px"><UploadFilled /></el-icon>
        <div>拖拽或点击上传 CSV 文件</div>
      </el-upload>
      <el-button type="primary" @click="doUpload" :loading="uploading" :disabled="!file" style="margin-top:12px">
        {{ uploading ? '处理中...' : '上传并导入' }}
      </el-button>
      <el-button @click="doPreprocess" :loading="preprocessing" style="margin-top:12px;margin-left:10px">
        🔄 一键预处理已有数据
      </el-button>
    </el-card>

    <!-- 数据表格 -->
    <el-card class="card-dark">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>📋 我的睡眠数据</span>
          <el-pagination v-model:current-page="page" :page-size="30" :total="total" small layout="prev,pager,next" @current-change="fetchData" />
        </div>
      </template>
      <el-table :data="records" stripe max-height="500" v-loading="loading" empty-text="暂无数据，请上传 CSV 文件">
        <el-table-column prop="record_date" label="日期" width="120" sortable />
        <el-table-column prop="sleepQualityScore" label="质量分" width="90" sortable>
          <template #default="{ row }"><el-tag :type="row.sleepQualityScore>=80?'success':row.sleepQualityScore>=60?'warning':'danger'" size="small">{{ row.sleepQualityScore }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="totalSleepMinutes" label="总睡眠" width="90" />
        <el-table-column prop="deepSleepTime" label="深睡" width="70" />
        <el-table-column prop="shallowSleepTime" label="浅睡" width="70" />
        <el-table-column prop="REMTime" label="REM" width="70" />
        <el-table-column prop="wakeTime" label="清醒" width="70" />
        <el-table-column prop="sleepEfficiency" label="效率" width="80">
          <template #default="{ row }">{{ (row.sleepEfficiency*100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column prop="daySteps" label="步数" width="80" />
        <el-table-column prop="avgHeartRate" label="心率" width="70" />
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="确定删除？" @confirm="doDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { uploadCsv, getRecords, deleteRecord, runPreprocess } from '../api/sleep'
import { ElMessage } from 'element-plus'

const file = ref(null)
const uploading = ref(false)
const preprocessing = ref(false)
const loading = ref(false)
const records = ref([])
const page = ref(1)
const total = ref(0)

function onFileChange(f) { file.value = f.raw }
async function doUpload() {
  if (!file.value) return
  uploading.value = true
  try { const r = await uploadCsv(file.value); ElMessage.success(r.data.message); file.value = null; fetchData() }
  catch (e) { ElMessage.error(e.response?.data?.error || '上传失败') }
  finally { uploading.value = false }
}
async function doPreprocess() {
  preprocessing.value = true
  try { const r = await runPreprocess(); ElMessage.success(r.data.message); fetchData() }
  catch (e) { ElMessage.error(e.response?.data?.error || '预处理失败') }
  finally { preprocessing.value = false }
}
async function fetchData(p = 1) { page.value = p; loading.value = true; try { const r = await getRecords(p, 30); records.value = r.data.data; total.value = r.data.total } catch (e) {} finally { loading.value = false } }
async function doDelete(id) { try { await deleteRecord(id); ElMessage.success('已删除'); fetchData() } catch (e) { ElMessage.error('删除失败') } }
onMounted(() => fetchData())
</script>
