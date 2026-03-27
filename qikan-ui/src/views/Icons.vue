<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>⚙️ 图标管理</h2>
      <el-button type="primary" @click="loadIcons">🔄 刷新</el-button>
    </div>

    <div class="admin-content">
      <el-alert
        title="图标管理说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #default>
          <p>1. 点击图标可预览大图</p>
          <p>2. 上传图片后会自动更新配置</p>
          <p>3. 留空图片路径将恢复使用Emoji</p>
          <p>4. 修改Emoji后点击保存</p>
        </template>
      </el-alert>

      <div class="icon-grid">
        <div v-for="(icon, key) in icons" :key="key" class="icon-card">
          <div class="icon-preview" @click="previewIcon(key)">
            <img v-if="icon.image" :src="icon.image" :alt="icon.name" />
            <span v-else class="emoji">{{ icon.emoji }}</span>
          </div>
          <div class="icon-info">
            <div class="icon-name">{{ icon.name }}</div>
            <div class="icon-key">{{ key }}</div>
          </div>
          <div class="icon-actions">
            <el-upload
              :action="uploadUrl"
              :data="{ icon_key: key }"
              :headers="uploadHeaders"
              :show-file-list="false"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              accept=".png,.jpg,.jpeg,.gif,.svg,.webp"
            >
              <el-button size="small">上传图片</el-button>
            </el-upload>
          </div>
          <div class="icon-edit">
            <el-input
              v-model="icon.emoji"
              placeholder="Emoji"
              size="small"
              style="width: 80px"
            />
            <el-button size="small" type="primary" @click="saveIcon(key)">
              保存
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="previewVisible" title="预览图标" width="400px">
      <div class="preview-content">
        <img v-if="previewImage" :src="previewImage" alt="预览" class="preview-img" />
        <span v-else class="preview-emoji">{{ previewEmoji }}</span>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()

const icons = ref({})
const previewVisible = ref(false)
const previewImage = ref('')
const previewEmoji = ref('')
const uploadUrl = '/api/admin/icons/upload'
const adminToken = localStorage.getItem('qikan_admin_token') || ''

const uploadHeaders = {
  'X-Admin-Token': adminToken
}

const api = axios.create({
  baseURL: '',
  timeout: 10000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('qikan_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      ElMessage.error('请先登录管理员账号')
      router.push('/')
    }
    return Promise.reject(err)
  }
)

const checkAdmin = async () => {
  if (!adminToken) {
    ElMessage.error('需要管理员权限')
    router.push('/home')
    return false
  }
  try {
    const res = await api.post('/api/admin/verify-token', { admin_token: adminToken })
    if (!res.success) {
      ElMessage.error('管理员权限验证失败')
      router.push('/home')
      return false
    }
    return true
  } catch (e) {
    ElMessage.error('管理员权限验证失败')
    router.push('/home')
    return false
  }
}

const loadIcons = async () => {
  try {
    const res = await api.get('/api/icons/config')
    if (res.success) {
      icons.value = res.config.icons || {}
    } else {
      ElMessage.error(res.message || '加载失败')
    }
  } catch (e) {
    ElMessage.error('加载图标配置失败')
  }
}

const previewIcon = (key) => {
  const icon = icons.value[key]
  if (icon.image) {
    previewImage.value = icon.image
    previewEmoji.value = ''
  } else {
    previewImage.value = ''
    previewEmoji.value = icon.emoji
  }
  previewVisible.value = true
}

const handleUploadSuccess = (res) => {
  if (res.success) {
    ElMessage.success('上传成功')
    loadIcons()
  } else {
    ElMessage.error(res.message || '上传失败')
  }
}

const handleUploadError = () => {
  ElMessage.error('上传失败')
}

const saveIcon = async (key) => {
  try {
    const res = await api.post('/api/admin/icons/update', {
      admin_token: adminToken,
      icon_key: key,
      emoji: icons.value[key].emoji,
      image: icons.value[key].image
    })
    if (res.success) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

onMounted(async () => {
  const isAdmin = await checkAdmin()
  if (isAdmin) {
    loadIcons()
  }
})
</script>

<style scoped>
.view-container {
  min-height: 100vh;
  background: #1a1a2e;
  padding: 20px;
}

.nav-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.nav-bar h2 {
  color: #ffd700;
  margin: 0;
}

.admin-content {
  background: #16213e;
  border-radius: 12px;
  padding: 20px;
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.icon-card {
  background: #1a2a4a;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.icon-preview {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0d1525;
  border-radius: 8px;
  cursor: pointer;
  overflow: hidden;
}

.icon-preview img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.emoji {
  font-size: 32px;
}

.icon-info {
  text-align: center;
}

.icon-name {
  color: #fff;
  font-size: 14px;
  font-weight: bold;
}

.icon-key {
  color: #6b7280;
  font-size: 12px;
}

.icon-actions {
  width: 100%;
  display: flex;
  justify-content: center;
}

.icon-edit {
  display: flex;
  gap: 8px;
  align-items: center;
}

.preview-content {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.preview-img {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
}

.preview-emoji {
  font-size: 100px;
}
</style>
