<template>
  <div class="page">
    <h2 style="margin-bottom:20px">📁 数据管理</h2>
    <!-- 上传区域 -->
    <el-card class="card-dark" style="margin-bottom:20px">
      <template #header>📤 上传睡眠数据</template>
      <el-tabs v-model="uploadMode" type="border-card">
        <!-- 单个 CSV 上传 -->
        <el-tab-pane label="📄 单个CSV" name="single">
          <el-upload drag :auto-upload="false" :on-change="onFileChange" :limit="1" accept=".csv">
            <el-icon style="font-size:48px"><UploadFilled /></el-icon>
            <div>拖拽或点击上传 CSV 文件</div>
          </el-upload>
          <el-button type="primary" @click="doUpload" :loading="uploading" :disabled="!singleFile" style="margin-top:12px">
            {{ uploading ? '处理中...' : '上传并导入' }}
          </el-button>
        </el-tab-pane>

        <!-- ZIP 压缩包上传 -->
        <el-tab-pane label="📦 ZIP压缩包" name="zip">
          <el-upload drag :auto-upload="false" :on-change="onZipChange" :limit="1" accept=".zip">
            <el-icon style="font-size:48px"><FolderOpened /></el-icon>
            <div>拖拽或点击上传 ZIP 压缩包（内含CSV文件）</div>
          </el-upload>
          <el-button type="primary" @click="doUploadZip" :loading="zipUploading" :disabled="!zipFile" style="margin-top:12px">
            {{ zipUploading ? '解压分析中...' : '上传ZIP并导入' }}
          </el-button>
        </el-tab-pane>

        <!-- 多文件上传 -->
        <el-tab-pane label="📋 多个CSV" name="multi">
          <el-upload drag :auto-upload="false" :on-change="onMultiChange" multiple accept=".csv">
            <el-icon style="font-size:48px"><UploadFilled /></el-icon>
            <div>拖拽或点击上传多个 CSV 文件</div>
          </el-upload>
          <div v-if="multiFiles.length" style="margin-top:8px;color:#889">
            已选择 {{ multiFiles.length }} 个文件：
            <el-tag v-for="f in multiFiles" :key="f.name" size="small" style="margin:2px">{{ f.name }}</el-tag>
          </div>
          <el-button type="primary" @click="doUploadMulti" :loading="multiUploading" :disabled="!multiFiles.length" style="margin-top:12px">
            {{ multiUploading ? '批量导入中...' : `上传 ${multiFiles.length} 个文件` }}
          </el-button>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 一键处理 -->
    <el-card class="card-dark" style="margin-bottom:20px">
      <template #header>⚡ 一键处理</template>
      <p style="color:#889;margin-bottom:10px">上传完成后，点击下方按钮自动完成预处理、特征计算、分析生成可视化数据。</p>
      <el-button type="success" @click="doProcessAll" :loading="processing">
        🚀 一键处理全部数据
      </el-button>
      <el-button @click="doPreprocess" :loading="preprocessing" style="margin-left:10px">
        🔄 仅重算衍生指标
      </el-button>
    </el-card>

    <!-- 处理结果 -->
    <el-card class="card-dark" style="margin-bottom:20px" v-if="processResult">
      <template #header>📊 处理结果</template>
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="6" v-for="c in resultCards" :key="c.label">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value" style="font-size:1.5rem">{{ c.value }}</div>
        </el-col>
      </el-row>
      <div v-if="processResult.stage_distribution" style="margin-top:16px">
        <strong>睡眠阶段分布：</strong>
        <el-tag v-for="s in processResult.stage_distribution" :key="s.name" style="margin:4px" size="small">
          {{ s.name }}: {{ s.value }}分钟 ({{ s.percent }}%)
        </el-tag>
      </div>
    </el-card>

    <!-- 数据表格 -->
    <el-card class="card-dark">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>📋 我的睡眠数据</span>
          <el-pagination v-model:current-page="page" :page-size="30" :total="total" small layout="prev,pager,next" @current-change="fetchData" />
        </div>
      </template>
      <el-table :data="records" stripe max-height="500" v-loading="loading" empty-text="暂无数据，请上传 CSV/ZIP 文件">
        <el-table-column prop="record_date" label="日期" width="120" sortable />
        <el-table-column prop="sleepQualityScore" label="质量分" width="90" sortable>
          <template #default="{ row }"><el-tag :type="row.sleepQualityScore>=8?'success':row.sleepQualityScore>=5?'warning':'danger'" size="small">{{ row.sleepQualityScore }}</el-tag></template>
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
import { ref, computed, onMounted } from 'vue'
import { uploadCsv, uploadZip, uploadMulti, getRecords, deleteRecord, runPreprocess, processAll } from '../api/sleep'
import { ElMessage } from 'element-plus'

const uploadMode = ref('single')
const singleFile = ref(null)
const zipFile = ref(null)
const multiFiles = ref([])
const uploading = ref(false)
const zipUploading = ref(false)
const multiUploading = ref(false)
const preprocessing = ref(false)
const processing = ref(false)
const loading = ref(false)
const records = ref([])
const page = ref(1)
const total = ref(0)
const processResult = ref(null)

const resultCards = computed(() => {
  if (!processResult.value?.summary) return []
  const s = processResult.value.summary
  return [
    { label: '记录条数', value: s.total_records },
    { label: '平均质量分', value: s.avg_quality_score },
    { label: '平均睡眠(分钟)', value: s.avg_sleep_minutes },
    { label: '平均效率', value: (s.avg_efficiency * 100).toFixed(1) + '%' },
  ]
})

function onFileChange(f) { singleFile.value = f.raw }
function onZipChange(f) { zipFile.value = f.raw }
function onMultiChange(f) {
  // el-upload multiple mode accumulates files
  multiFiles.value = [...multiFiles.value, f.raw]
}

async function doUpload() {
  if (!singleFile.value) return
  uploading.value = true
  try { const r = await uploadCsv(singleFile.value); ElMessage.success(r.data.message); singleFile.value = null; fetchData() }
  catch (e) { ElMessage.error(e.response?.data?.error || '上传失败') }
  finally { uploading.value = false }
}

async function doUploadZip() {
  if (!zipFile.value) return
  zipUploading.value = true
  try { const r = await uploadZip(zipFile.value); ElMessage.success(r.data.message); zipFile.value = null; fetchData() }
  catch (e) { ElMessage.error(e.response?.data?.error || 'ZIP处理失败') }
  finally { zipUploading.value = false }
}

async function doUploadMulti() {
  if (!multiFiles.value.length) return
  multiUploading.value = true
  try { const r = await uploadMulti(multiFiles.value); ElMessage.success(r.data.message); multiFiles.value = []; fetchData() }
  catch (e) { ElMessage.error(e.response?.data?.error || '批量上传失败') }
  finally { multiUploading.value = false }
}

async function doPreprocess() {
  preprocessing.value = true
  try { const r = await runPreprocess(); ElMessage.success(r.data.message); fetchData() }
  catch (e) { ElMessage.error(e.response?.data?.error || '预处理失败') }
  finally { preprocessing.value = false }
}

async function doProcessAll() {
  processing.value = true
  try {
    const r = await processAll()
    ElMessage.success(r.data.message)
    processResult.value = r.data
    fetchData()
  } catch (e) { ElMessage.error(e.response?.data?.error || '一键处理失败') }
  finally { processing.value = false }
}

async function fetchData(p = 1) { page.value = p; loading.value = true; try { const r = await getRecords(p, 30); records.value = r.data.data; total.value = r.data.total } catch (e) {} finally { loading.value = false } }
async function doDelete(id) { try { await deleteRecord(id); ElMessage.success('已删除'); fetchData() } catch (e) { ElMessage.error('删除失败') } }
onMounted(() => fetchData())
</script>
