<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>⚙️ 设置</h2>
      <el-button type="warning" @click="showAdminLogin = true">🔐 管理员</el-button>
    </div>

    <!-- 管理员登录对话框 -->
    <el-dialog v-model="showAdminLogin" title="管理员登录" width="400px">
      <el-alert
        title="管理员功能说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #default>
          <p>普通玩家也可以使用音效设置，不需要登录管理员</p>
          <p>管理员可配置音效文件、上传图标等</p>
        </template>
      </el-alert>
      <el-form label-width="80px">
        <el-form-item label="账号">
          <el-input v-model="adminLoginForm.account" placeholder="管理员账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="adminLoginForm.password" type="password" placeholder="管理员密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdminLogin = false">取消</el-button>
        <el-button type="primary" @click="handleAdminLogin" :loading="adminLoginLoading">登录</el-button>
      </template>
    </el-dialog>

    <!-- 音效设置 - 所有玩家都可使用 -->
    <el-card class="audio-main-card">
      <template #header>
        <div class="card-header-title">
          <span>🎵 音效与音乐设置</span>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="12">
          <div class="setting-item large">
            <div class="setting-info">
              <span class="setting-icon">🔊</span>
              <span class="setting-text">游戏音效</span>
            </div>
            <el-switch v-model="audioEnabled" @change="handleAudioToggle" />
          </div>
        </el-col>
        <el-col :span="12">
          <div class="setting-item large">
            <div class="setting-info">
              <span class="setting-icon">🎶</span>
              <span class="setting-text">背景音乐</span>
            </div>
            <el-switch v-model="musicEnabled" @change="handleMusicToggle" />
          </div>
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <div class="setting-item">
            <span class="setting-label">🔊 音效音量: {{ Math.round(soundVolume * 100) }}%</span>
            <el-slider v-model="soundVolume" :min="0" :max="1" :step="0.1" @change="handleSoundVolumeChange" />
          </div>
        </el-col>
        <el-col :span="12">
          <div class="setting-item">
            <span class="setting-label">🎵 音乐音量: {{ Math.round(musicVolume * 100) }}%</span>
            <el-slider v-model="musicVolume" :min="0" :max="1" :step="0.1" @change="handleMusicVolumeChange" />
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 角色设置 -->
    <el-card class="audio-main-card" style="margin-top: 20px">
      <template #header>
        <div class="card-header-title">
          <span>⚙️ 角色设置</span>
        </div>
      </template>
      
      <!-- 头像上传 -->
      <div class="avatar-upload-section">
        <h4>👤 玩家头像</h4>
        <div class="avatar-preview-area">
          <div class="avatar-preview">
            <img v-if="avatarPreview" :src="avatarPreview" alt="头像预览" />
            <div v-else class="avatar-placeholder">{{ player?.name?.slice(0, 1) || '?' }}</div>
          </div>
          <div class="avatar-upload-controls">
            <input type="file" ref="avatarFileInput" accept="image/jpeg,image/png,image/gif,image/webp" @change="handleAvatarSelect" style="display: none" />
            <el-button type="primary" @click="$refs.avatarFileInput.click()">选择文件</el-button>
            <el-button type="success" @click="uploadAvatar" :loading="avatarUploading" :disabled="!selectedAvatarFile">上传</el-button>
            <span class="avatar-hint">支持 JPG/PNG/GIF/WEBP，最大 2MB</span>
          </div>
        </div>
        <p class="avatar-note">上传后头像将显示在大地图和角色主页</p>
      </div>
      
      <el-divider />
      
      <div class="setting-item danger-zone">
        <div class="setting-info">
          <span class="setting-icon">🗑️</span>
          <span class="setting-text">清档重选出身</span>
          <span class="setting-desc">删除当前角色数据，重新选择出身（此操作不可恢复）</span>
        </div>
        <el-button type="danger" @click="handleResetCharacter" :loading="resetLoading">
          清档
        </el-button>
      </div>
    </el-card>

    <!-- 管理员功能区域 - 仅管理员可见 -->
    <template v-if="isAdmin">
      <el-divider />
      
      <el-alert
        title="管理员功能已解锁"
        type="success"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #default>
          <p>您已登录为管理员，可以使用以下管理功能</p>
        </template>
      </el-alert>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane v-if="adminLevel >= 5" label="🎵 音效文件配置" name="audio">
          <el-card header="音效文件配置 (仅LV5管理员)" class="audio-card">
            <el-form label-width="120px">
              <el-form-item label="获得第纳尔">
                <el-input v-model="audioConfig.sound_coins" placeholder="/static/audio/coins.mp3" />
                <el-button size="small" @click="saveAudioFile('sound_coins', audioConfig.sound_coins)">保存</el-button>
              </el-form-item>
              <el-form-item label="点击按钮">
                <el-input v-model="audioConfig.sound_button" placeholder="/static/audio/click.mp3" />
                <el-button size="small" @click="saveAudioFile('sound_button', audioConfig.sound_button)">保存</el-button>
              </el-form-item>
              <el-form-item label="接取任务">
                <el-input v-model="audioConfig.sound_task" placeholder="/static/audio/task.mp3" />
                <el-button size="small" @click="saveAudioFile('sound_task', audioConfig.sound_task)">保存</el-button>
              </el-form-item>
              <el-form-item label="穿戴装备">
                <el-input v-model="audioConfig.sound_equip" placeholder="/static/audio/equip.mp3" />
                <el-button size="small" @click="saveAudioFile('sound_equip', audioConfig.sound_equip)">保存</el-button>
              </el-form-item>
              <el-form-item label="攻击战斗">
                <el-input v-model="audioConfig.sound_attack" placeholder="/static/audio/attack.mp3" />
                <el-button size="small" @click="saveAudioFile('sound_attack', audioConfig.sound_attack)">保存</el-button>
              </el-form-item>
              <el-form-item label="背景音乐">
                <el-input v-model="audioConfig.music_bgm" placeholder="/static/audio/bgm.mp3" />
                <el-button size="small" @click="saveAudioFile('music_bgm', audioConfig.music_bgm)">保存</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>
        
        <el-tab-pane v-if="adminLevel >= 3" label="🖼️ 图标管理" name="icons">
          <el-button type="primary" @click="loadIcons">🔄 刷新</el-button>
          <el-alert
            title="图标管理说明"
            type="info"
            :closable="false"
            style="margin: 20px 0"
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
                <el-input v-model="icons[key].emoji" placeholder="Emoji" size="small" style="margin-top: 5px" />
                <el-input v-model="icons[key].image" placeholder="图片URL" size="small" style="margin-top: 5px" />
                <el-button v-if="canUpload" size="small" type="primary" @click="saveIcon(key)" style="margin-top: 5px">保存</el-button>
              </div>
            </div>
          </div>

          <el-dialog v-model="previewVisible" title="图标预览" width="400px">
            <div class="preview-content">
              <img v-if="previewImage" :src="previewImage" alt="预览" style="max-width: 100%" />
              <span v-else-if="previewEmoji" class="preview-emoji">{{ previewEmoji }}</span>
            </div>
          </el-dialog>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { useGameStore } from '../stores/game'
import { useAudioStore } from '../stores/audio'

const router = useRouter()
const gameStore = useGameStore()
const audioStore = useAudioStore()
const resetLoading = ref(false)

// 头像上传
const player = ref(null)
const avatarPreview = ref('')
const selectedAvatarFile = ref(null)
const avatarFileInput = ref(null)
const avatarUploading = ref(false)

const handleAvatarSelect = (event) => {
  const file = event.target.files[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 2MB')
    return
  }
  selectedAvatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
}

const uploadAvatar = async () => {
  if (!selectedAvatarFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  avatarUploading.value = true
  try {
    const formData = new FormData()
    formData.append('avatar', selectedAvatarFile.value)
    const res = await fetch('/api/avatar/upload', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${gameStore.token}` },
      body: formData,
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('头像上传成功')
      avatarPreview.value = data.avatar_url
      // 刷新玩家数据
      await gameStore.getPanel()
      player.value = gameStore.player
    } else {
      ElMessage.error(data.message || '上传失败')
    }
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    avatarUploading.value = false
  }
}

const handleResetCharacter = async () => {
  try {
    await ElMessageBox.confirm(
      '此操作将删除当前角色并重置到初始状态，是否继续？',
      '⚠️ 确认清档',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      }
    )
    
    resetLoading.value = true
    const res = await fetch('/api/reset-character', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: gameStore.token })
    })
    const data = await res.json()
    
    if (data.success) {
      ElMessage.success('角色已重置，请重新选择出身')
      sessionStorage.setItem('needsSpawn', '1')
      sessionStorage.removeItem('spawn_completed')
      router.push('/home')
    } else {
      ElMessage.error(data.message || '重置失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  } finally {
    resetLoading.value = false
  }
}

const activeTab = ref('audio')

const icons = ref({})
const previewVisible = ref(false)
const previewImage = ref('')
const previewEmoji = ref('')
const uploadUrl = '/api/admin/icons/upload'
const adminToken = ref(localStorage.getItem('qikan_admin_token') || '')
const canUpload = ref(false)
const isAdmin = ref(false)
const adminLevel = ref(0)
const adminLoginLoading = ref(false)
const showAdminLogin = ref(false)
const adminLoginForm = ref({
  account: '',
  password: ''
})

const audioEnabled = ref(false)
const musicEnabled = ref(false)
const soundVolume = ref(0.7)
const musicVolume = ref(0.5)
const audioConfig = ref({
  sound_coins: '',
  sound_button: '',
  sound_task: '',
  sound_equip: '',
  sound_attack: '',
  music_bgm: ''
})

const loadAudioConfig = async () => {
  try {
    const resp = await fetch('/api/audio/config')
    const data = await resp.json()
    if (data.success) {
      audioEnabled.value = data.data.enabled
      musicEnabled.value = data.data.music_enabled
      soundVolume.value = data.data.sound_volume
      musicVolume.value = data.data.music_volume
      audioConfig.value.sound_coins = data.data.sound_coins || ''
      audioConfig.value.sound_button = data.data.sound_button || ''
      audioConfig.value.sound_task = data.data.sound_task || ''
      audioConfig.value.sound_equip = data.data.sound_equip || ''
      audioConfig.value.sound_attack = data.data.sound_attack || ''
      audioConfig.value.music_bgm = data.data.music_bgm || ''
    }
  } catch (e) {
    console.error('加载音效配置失败', e)
  }
}

const handleAudioToggle = (val) => {
  audioStore.toggleSound(val)
}

const handleMusicToggle = (val) => {
  audioStore.toggleMusic(val)
}

const handleSoundVolumeChange = (val) => {
  audioStore.setSoundVolume(val)
}

const handleMusicVolumeChange = (val) => {
  audioStore.setMusicVolume(val)
}

const saveAudioFile = async (type, path) => {
  if (!adminToken.value) {
    ElMessage.error('请先登录管理员')
    return
  }
  try {
    const resp = await fetch('/api/admin/audio/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_token: adminToken.value,
        audio_type: type,
        file_path: path
      })
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success('音效文件配置已保存')
    } else {
      ElMessage.error(data.message || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const uploadHeaders = {
  'X-Admin-Token': adminToken.value
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
  if (!adminToken.value) {
    return false
  }
  try {
    const res = await api.post('/api/admin/verify-token', { admin_token: adminToken.value })
    if (!res.success) {
      return false
    }
    adminLevel.value = res.level || 0
    canUpload.value = res.can_upload_icons || false
    return true
  } catch (e) {
    return false
  }
}

const handleAdminLogin = async () => {
  if (!adminLoginForm.value.account || !adminLoginForm.value.password) {
    ElMessage.warning('请输入管理员账号和密码')
    return
  }
  adminLoginLoading.value = true
  try {
    const res = await api.post('/api/admin/login', {
      account: adminLoginForm.value.account,
      password: adminLoginForm.value.password
    })
    if (res.success) {
      adminToken.value = res.admin_token || res.token
      localStorage.setItem('qikan_admin_token', adminToken.value)
      const verifyRes = await api.post('/api/admin/verify-token', { admin_token: adminToken.value })
      if (verifyRes.success) {
        adminLevel.value = verifyRes.level || 0
        isAdmin.value = true
        showAdminLogin.value = false
        adminLoginForm.value = { account: '', password: '' }
        ElMessage.success('管理员登录成功')
        loadIcons()
        loadAudioConfig()
      } else {
        ElMessage.error('登录成功但权限验证失败')
      }
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch (e) {
    ElMessage.error('登录失败，请检查账号密码')
  } finally {
    adminLoginLoading.value = false
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
  if (!gameStore.token) {
    router.push('/')
    return
  }
  if (!gameStore.connected) {
    await gameStore.connectWs()
  }
  await gameStore.getPanel()
  player.value = gameStore.player
  if (player.value?.avatar_url) {
    avatarPreview.value = player.value.avatar_url
  }
  const isAdminResult = await checkAdmin()
  isAdmin.value = isAdminResult
  await loadAudioConfig()
  if (isAdminResult) {
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

.card-header-title {
  font-size: 16px;
  font-weight: bold;
  color: #ffd700;
}

.audio-main-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.setting-item.large {
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.setting-icon {
  font-size: 28px;
}

.setting-text {
  font-size: 16px;
  color: #e0e0e0;
  font-weight: bold;
}

.avatar-upload-section {
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.avatar-upload-section h4 {
  color: #d4a464;
  margin: 0 0 16px;
}

.avatar-preview-area {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.avatar-preview {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid #d4a464;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  font-size: 36px;
  color: #ffd700;
}

.avatar-upload-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.avatar-hint {
  font-size: 12px;
  color: #666;
}

.avatar-note {
  font-size: 12px;
  color: #888;
  margin: 8px 0 0;
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

.danger-zone {
  padding: 20px;
  background: rgba(139, 0, 0, 0.1);
  border: 1px solid rgba(139, 0, 0, 0.3);
  border-radius: 10px;
}

.danger-zone .setting-info {
  flex-direction: column;
  align-items: flex-start;
}

.danger-zone .setting-desc {
  color: #888;
  font-size: 12px;
  margin-top: 5px;
}
</style>
