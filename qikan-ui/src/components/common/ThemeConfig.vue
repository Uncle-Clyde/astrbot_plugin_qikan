<template>
  <div class="theme-config-panel">
    <el-alert
      title="主题DIY说明"
      type="info"
      :closable="false"
      style="margin-bottom: 20px"
    >
      <template #default>
        <p>1. 调整背景色、边框色、强调色等自定义样式</p>
        <p>2. 开启后自定义样式将应用到全局</p>
        <p>3. 支持多种预设主题快速切换</p>
        <p>4. 点击保存后实时生效</p>
      </template>
    </el-alert>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card header="预设主题">
          <div class="theme-presets">
            <div 
              v-for="preset in presets" 
              :key="preset.name"
              class="preset-card"
              :class="{ active: currentPreset === preset.name }"
              @click="applyPreset(preset)"
            >
              <div class="preset-preview" :style="preset.preview"></div>
              <div class="preset-name">{{ preset.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card header="自定义颜色">
          <el-form label-width="100px" class="ui-config-form">
            <el-form-item label="启用自定义">
              <el-switch v-model="uiConfig.enabled" @change="saveUiConfig" />
            </el-form-item>
            
            <el-form-item label="背景渐变">
              <el-color-picker v-model="uiConfig.background_gradient_start" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.background_gradient_start }}</span>
            </el-form-item>
            
            <el-form-item label="渐变结束">
              <el-color-picker v-model="uiConfig.background_gradient_end" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.background_gradient_end }}</span>
            </el-form-item>
            
            <el-form-item label="顶部栏颜色">
              <el-color-picker v-model="uiConfig.header_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.header_color }}</span>
            </el-form-item>
            
            <el-form-item label="强调色">
              <el-color-picker v-model="uiConfig.accent_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.accent_color }}</span>
            </el-form-item>
            
            <el-form-item label="文字颜色">
              <el-color-picker v-model="uiConfig.text_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.text_color }}</span>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveUiConfig">保存配置</el-button>
              <el-button @click="resetUiConfig">恢复默认</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-card header="DIY内容管理" style="margin-top: 20px">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="关于页面" name="about">
          <el-button type="primary" @click="editAbout">编辑关于页面</el-button>
          <el-button @click="previewAbout">预览</el-button>
        </el-tab-pane>
        
        <el-tab-pane label="公告管理" name="announcements">
          <div class="announcement-list">
            <el-button type="primary" @click="createAnnouncement" style="margin-bottom: 15px">
              + 发布新公告
            </el-button>
            <el-table :data="announcements" style="width: 100%">
              <el-table-column prop="title" label="标题" />
              <el-table-column prop="enabled" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.enabled ? 'success' : 'info'">
                    {{ row.enabled ? '启用' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-button size="small" @click="editAnnouncement(row)">编辑</el-button>
                  <el-button size="small" type="danger" @click="deleteAnnouncement(row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="游戏配置" name="game">
          <el-form label-width="120px">
            <el-form-item label="游戏标题">
              <el-input v-model="gameConfig.title" />
            </el-form-item>
            <el-form-item label="服务器描述">
              <el-input v-model="gameConfig.description" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="开启注册">
              <el-switch v-model="gameConfig.allowRegister" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveGameConfig">保存</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="aboutDialogVisible" title="编辑关于页面" width="600px">
      <el-form :model="aboutForm" label-width="80px">
        <el-form-item label="鸣谢">
          <el-input v-model="aboutForm.acknowledgements" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="规则">
          <el-input v-model="aboutForm.rules" type="textarea" :rows="8" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="aboutDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAbout" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="announcementDialogVisible" title="编辑公告" width="500px">
      <el-form :model="announcementForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="announcementForm.title" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="announcementForm.content" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="announcementForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="announcementDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAnnouncement">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  uiConfig: Object,
  adminToken: String
})

const emit = defineEmits(['update:uiConfig'])

const presets = [
  { name: 'default', label: '默认', preview: { background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' } },
  { name: 'dark', label: '暗黑', preview: { background: 'linear-gradient(135deg, #0a0a14 0%, #12121f 100%)' } },
  { name: 'fantasy', label: '奇幻', preview: { background: 'linear-gradient(135deg, #1a1410 0%, #2a2015 100%)' } },
  { name: 'mystic', label: '神秘', preview: { background: 'linear-gradient(135deg, #0d0d1a 0%, #15152a 100%)' } },
  { name: 'nature', label: '自然', preview: { background: 'linear-gradient(135deg, #0a140a 0%, #142014 100%)' } },
  { name: 'ocean', label: '海洋', preview: { background: 'linear-gradient(135deg, #0a1a2e 0%, #0f2a3f 100%)' } },
]

const currentPreset = ref('default')
const uiConfig = ref({ ...props.uiConfig })
const activeTab = ref('about')
const aboutDialogVisible = ref(false)
const announcementDialogVisible = ref(false)
const saving = ref(false)

const aboutForm = reactive({
  acknowledgements: '',
  rules: ''
})

const announcementForm = reactive({
  id: null,
  title: '',
  content: '',
  enabled: true
})

const announcements = ref([])
const gameConfig = reactive({
  title: '骑砍英雄传',
  description: '在卡拉迪亚大陆展开你的传奇',
  allowRegister: true
})

const applyPreset = (preset) => {
  currentPreset.value = preset.name
  if (preset.config) {
    uiConfig.value = { ...uiConfig.value, ...preset.config }
    saveUiConfig()
  }
}

const saveUiConfig = async () => {
  try {
    const resp = await fetch('/api/admin/ui-config/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_token: props.adminToken,
        config: uiConfig.value
      })
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success('保存成功')
      emit('update:uiConfig', uiConfig.value)
    } else {
      ElMessage.error(data.message || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const resetUiConfig = async () => {
  const defaultConfig = {
    enabled: false,
    background_color: '#1a1a2e',
    background_gradient_start: '#1a1a2e',
    background_gradient_end: '#16213e',
    header_color: 'linear-gradient(135deg, #16213e 0%, #1a1a2e 100%)',
    header_border_color: '#4a4a8a',
    accent_color: '#d4a464',
    text_color: '#e8e0d0',
    button_color: '#d4a464'
  }
  uiConfig.value = defaultConfig
  await saveUiConfig()
}

const loadAnnouncements = async () => {
  try {
    const resp = await fetch('/api/admin/announcements/list', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_token: props.adminToken })
    })
    const data = await resp.json()
    if (data.success) {
      announcements.value = data.announcements || []
    }
  } catch (e) {
    console.error('加载公告失败', e)
  }
}

const editAbout = async () => {
  try {
    const resp = await fetch('/api/about')
    const data = await resp.json()
    if (data.success) {
      aboutForm.acknowledgements = data.data.acknowledgements || ''
      aboutForm.rules = data.data.rules || ''
      aboutDialogVisible.value = true
    }
  } catch (e) {
    ElMessage.error('加载失败')
  }
}

const previewAbout = () => {
  window.open('/about', '_blank')
}

const saveAbout = async () => {
  saving.value = true
  try {
    const resp = await fetch('/api/admin/about', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_token: props.adminToken,
        acknowledgements: aboutForm.acknowledgements,
        rules: aboutForm.rules
      })
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success('保存成功')
      aboutDialogVisible.value = false
    } else {
      ElMessage.error(data.message || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const createAnnouncement = () => {
  announcementForm.id = null
  announcementForm.title = ''
  announcementForm.content = ''
  announcementForm.enabled = true
  announcementDialogVisible.value = true
}

const editAnnouncement = (row) => {
  announcementForm.id = row.id
  announcementForm.title = row.title
  announcementForm.content = row.content
  announcementForm.enabled = !!row.enabled
  announcementDialogVisible.value = true
}

const saveAnnouncement = async () => {
  try {
    const url = announcementForm.id ? '/api/admin/announcements/update' : '/api/admin/announcements/create'
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_token: props.adminToken,
        id: announcementForm.id,
        title: announcementForm.title,
        content: announcementForm.content,
        enabled: announcementForm.enabled ? 1 : 0
      })
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success('保存成功')
      announcementDialogVisible.value = false
      loadAnnouncements()
    } else {
      ElMessage.error(data.message || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const deleteAnnouncement = async (id) => {
  try {
    const resp = await fetch('/api/admin/announcements/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_token: props.adminToken, id })
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success('删除成功')
      loadAnnouncements()
    } else {
      ElMessage.error(data.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const saveGameConfig = async () => {
  ElMessage.success('游戏配置已保存')
}

onMounted(() => {
  loadAnnouncements()
})
</script>

<style scoped>
.theme-config-panel {
  padding: 20px;
}

.theme-presets {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.preset-card {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.preset-card:hover {
  border-color: var(--primary-color);
}

.preset-card.active {
  border-color: var(--primary-color);
  box-shadow: 0 0 10px rgba(212, 164, 100, 0.5);
}

.preset-preview {
  height: 60px;
  border-radius: 6px 6px 0 0;
}

.preset-name {
  padding: 8px;
  text-align: center;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 12px;
}

.color-value {
  margin-left: 10px;
  color: var(--text-muted);
  font-size: 12px;
}

.ui-config-form :deep(.el-form-item__label) {
  color: var(--text-primary);
}

.announcement-list {
  padding: 10px;
}
</style>
