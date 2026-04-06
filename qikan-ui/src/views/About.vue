<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>📖 关于页面</h2>
      <el-button v-if="isAdmin" type="primary" @click="showEditDialog = true">编辑</el-button>
    </div>

    <div class="about-content">
      <el-card class="about-card">
        <template #header>
          <div class="card-header">
            <span>🏆 鸣谢</span>
          </div>
        </template>
        <div class="content-text" v-html="formatContent(aboutData.acknowledgements)"></div>
        <el-empty v-if="!aboutData.acknowledgements" description="暂无鸣谢内容"></el-empty>
      </el-card>

      <el-card class="about-card">
        <template #header>
          <div class="card-header">
            <span>📜 规则介绍</span>
          </div>
        </template>
        <div class="content-text" v-html="formatContent(aboutData.rules)"></div>
        <el-empty v-if="!aboutData.rules" description="暂无规则内容"></el-empty>
      </el-card>

      <div class="update-time" v-if="aboutData.updated_at">
        最后更新：{{ formatTime(aboutData.updated_at) }}
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑关于页面" width="600px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="鸣谢">
          <el-input
            v-model="editForm.acknowledgements"
            type="textarea"
            :rows="6"
            placeholder="输入鸣谢内容，支持换行"
          />
        </el-form-item>
        <el-form-item label="规则">
          <el-input
            v-model="editForm.rules"
            type="textarea"
            :rows="8"
            placeholder="输入规则介绍，支持换行"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAbout" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useGameStore } from '../stores/game'

const gameStore = useGameStore()
const isAdmin = ref(false)
const showEditDialog = ref(false)
const saving = ref(false)

const aboutData = ref({
  acknowledgements: '',
  rules: '',
  updated_at: ''
})

const editForm = reactive({
  acknowledgements: '',
  rules: ''
})

const formatContent = (content) => {
  if (!content) return ''
  return content.replace(/\n/g, '<br>')
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  try {
    return new Date(timeStr).toLocaleString('zh-CN')
  } catch {
    return timeStr
  }
}

const loadAbout = async () => {
  try {
    const resp = await fetch('/api/about')
    const data = await resp.json()
    if (data.success) {
      aboutData.value = data.data
    }
  } catch (e) {
    console.error('加载关于页面失败:', e)
  }
}

const checkAdminStatus = async () => {
  const token = localStorage.getItem('admin_token')
  if (!token) {
    isAdmin.value = false
    return
  }
  try {
    const resp = await fetch('/api/admin/verify-token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_token: token })
    })
    const data = await resp.json()
    isAdmin.value = data.success && data.is_admin
  } catch {
    isAdmin.value = false
  }
}

const saveAbout = async () => {
  const token = localStorage.getItem('admin_token')
  if (!token) {
    ElMessage.error('请先登录管理员')
    return
  }

  saving.value = true
  try {
    const resp = await fetch('/api/admin/about', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_token: token,
        acknowledgements: editForm.acknowledgements,
        rules: editForm.rules
      })
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success('保存成功')
      showEditDialog.value = false
      loadAbout()
    } else {
      ElMessage.error(data.message || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadAbout()
  checkAdminStatus()
})
</script>

<style scoped>
.view-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
}

.nav-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.nav-bar h2 {
  color: #d4a464;
  margin: 0;
  flex: 1;
}

.about-content {
  max-width: 800px;
  margin: 0 auto;
}

.about-card {
  margin-bottom: 20px;
  background: rgba(18, 18, 42, 0.8);
  border: 1px solid #4a4a8a;
}

.about-card :deep(.el-card__header) {
  background: rgba(74, 74, 138, 0.3);
  border-bottom: 1px solid #4a4a8a;
  color: #d4a464;
  font-weight: bold;
}

.about-card :deep(.el-card__body) {
  padding: 20px;
}

.content-text {
  color: #e8e0d0;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.update-time {
  text-align: center;
  color: #6a6a8a;
  font-size: 12px;
  margin-top: 20px;
}
</style>
