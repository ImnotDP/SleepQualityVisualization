<template>
  <div class="page">
    <h2 style="margin-bottom:20px">👥 用户管理</h2>
    <el-card class="card-dark">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>全站用户列表</span>
          <el-pagination v-model:current-page="page" :page-size="50" :total="total" small layout="prev,pager,next" @current-change="fetchUsers" />
        </div>
      </template>
      <el-table :data="users" stripe max-height="500" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="role" label="角色" width="80">
          <template #default="{ row }"><el-tag :type="row.role==='admin'?'danger':'success'" size="small">{{ row.role }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="record_count" label="数据条数" width="90" />
        <el-table-column prop="report_count" label="报告数" width="80" />
        <el-table-column prop="avg_quality" label="平均质量分" width="110">
          <template #default="{ row }">
            <span :style="{color:row.avg_quality>=7?'#67c23a':row.avg_quality>=5?'#409eff':'#e6a23c',fontWeight:'bold'}">{{ row.avg_quality }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_record_date" label="最近记录日期" width="140" />
        <el-table-column prop="created_at" label="注册时间" width="180" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-popconfirm v-if="row.role!=='admin'" title="确定删除该用户及全部数据？" @confirm="doDelete(row.id)">
              <template #reference><el-button text type="danger" size="small">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 全局数据管理 -->
    <el-card class="card-dark" style="margin-top:20px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>🌐 全局睡眠数据</span>
          <el-select v-model="filterUserId" placeholder="按用户筛选" clearable @change="fetchRecords" style="width:200px">
            <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </div>
      </template>
      <el-table :data="records" stripe max-height="400" v-loading="recLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column prop="record_date" label="日期" width="120" />
        <el-table-column prop="sleepQualityScore" label="质量分" width="85">
          <template #default="{ row }">
            <el-tag :type="row.sleepQualityScore>=7?'success':row.sleepQualityScore>=5?'primary':'warning'" size="small">{{ row.sleepQualityScore }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalSleepMinutes" label="总睡眠" width="110">
          <template #default="{ row }">{{ formatMinutesShort(row.totalSleepMinutes) }}</template>
        </el-table-column>
        <el-table-column prop="deepSleepTime" label="深睡" width="90">
          <template #default="{ row }">{{ formatMinutesShort(row.deepSleepTime) }}</template>
        </el-table-column>
        <el-table-column label="REM" width="85">
          <template #default="{ row }">{{ formatMinutesShort(row.REMTime) }}</template>
        </el-table-column>
        <el-table-column prop="sleepEfficiency" label="效率" width="75">
          <template #default="{ row }">{{ row.sleepEfficiency ? (row.sleepEfficiency*100).toFixed(0)+'%' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="daySteps" label="步数" width="80" />
        <el-table-column prop="avgHeartRate" label="心率(bpm)" width="95" />
        <el-table-column prop="temperature" label="温度(°C)" width="95" />
        <el-table-column prop="spo2" label="血氧(%)" width="85" />
        <el-table-column label="操作" width="70">
          <template #default="{ row }">
            <el-popconfirm title="确定删除？" @confirm="doDeleteRec(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="recPage" :page-size="30" :total="recTotal" small layout="prev,pager,next" @current-change="fetchRecords" style="margin-top:10px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAdminUsers, deleteAdminUser, getAdminAllRecords, deleteAdminRecord } from '../api/sleep'
import { ElMessage } from 'element-plus'
import { formatMinutesShort } from '../utils/format'

const loading=ref(false), users=ref([]), page=ref(1), total=ref(0)
const recLoading=ref(false), records=ref([]), recPage=ref(1), recTotal=ref(0), filterUserId=ref(null)

async function fetchUsers(p=1) { page.value=p; loading.value=true; try{const r=await getAdminUsers(p,50); users.value=r.data.data; total.value=r.data.total}catch(e){}finally{loading.value=false} }
async function doDelete(id) { try{await deleteAdminUser(id); ElMessage.success('已删除'); fetchUsers()}catch(e){ElMessage.error('删除失败')} }
async function fetchRecords(p=1) { recPage.value=p; recLoading.value=true; try{const r=await getAdminAllRecords(p,30,filterUserId.value); records.value=r.data.data; recTotal.value=r.data.total}catch(e){}finally{recLoading.value=false} }
async function doDeleteRec(id) { try{await deleteAdminRecord(id); ElMessage.success('已删除'); fetchRecords()}catch(e){ElMessage.error('删除失败')} }

onMounted(()=>{fetchUsers();fetchRecords()})
</script>
