<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>⚙️ 管理面板</h2>
      <el-button type="primary" @click="checkAdminStatus">🔄 刷新</el-button>
    </div>

    <div class="admin-content" v-if="isAdmin">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="UI自定义" name="ui" v-if="canCustomizeUi">
          <el-alert
            title="UI自定义说明"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          >
            <template #default>
              <p>1. 调整背景色、边框色、强调色等</p>
              <p>2. 开启后自定义样式将应用到全局</p>
              <p>3. 点击保存后实时生效</p>
            </template>
          </el-alert>

          <el-form label-width="120px" class="ui-config-form">
            <el-form-item label="启用自定义">
              <el-switch v-model="uiConfig.enabled" @change="saveUiConfig" />
            </el-form-item>
            
            <el-form-item label="背景色">
              <el-color-picker v-model="uiConfig.background_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.background_color }}</span>
            </el-form-item>
            
            <el-form-item label="渐变起始色">
              <el-color-picker v-model="uiConfig.background_gradient_start" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.background_gradient_start }}</span>
            </el-form-item>
            
            <el-form-item label="渐变结束色">
              <el-color-picker v-model="uiConfig.background_gradient_end" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.background_gradient_end }}</span>
            </el-form-item>
            
            <el-form-item label="顶部栏颜色">
              <el-color-picker v-model="uiConfig.header_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.header_color }}</span>
            </el-form-item>
            
            <el-form-item label="顶部栏边框色">
              <el-color-picker v-model="uiConfig.header_border_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.header_border_color }}</span>
            </el-form-item>
            
            <el-form-item label="强调色">
              <el-color-picker v-model="uiConfig.accent_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.accent_color }}</span>
            </el-form-item>
            
            <el-form-item label="文字颜色">
              <el-color-picker v-model="uiConfig.text_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.text_color }}</span>
            </el-form-item>
            
            <el-form-item label="按钮颜色">
              <el-color-picker v-model="uiConfig.button_color" @change="saveUiConfig" />
              <span class="color-value">{{ uiConfig.button_color }}</span>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveUiConfig">保存配置</el-button>
              <el-button @click="resetUiConfig">恢复默认</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="管理员管理" name="admins" v-if="canManageAdmins">
          <el-alert
            title="管理员管理说明"
            type="warning"
            :closable="false"
            style="margin-bottom: 20px"
          >
            <template #default>
              <p>1. 只有创始人(lv5)可以管理管理员</p>
              <p>2. 可创建、修改等级、删除管理员</p>
              <p>3. 管理员等级：1-观察员 2-版主 3-管理员 4-超级管理员</p>
            </template>
          </el-alert>

          <el-button type="primary" @click="showCreateDialog" style="margin-bottom: 20px">
            + 创建管理员
          </el-button>

          <el-table :data="admins" style="width: 100%">
            <el-table-column prop="username" label="用户名" />
            <el-table-column prop="level" label="等级">
              <template #default="{ row }">
                <el-tag :type="getLevelTagType(row.level)">{{ row.level_name }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_by" label="创建者" />
            <el-table-column prop="last_login" label="最后登录">
              <template #default="{ row }">
                {{ row.last_login ? new Date(row.last_login * 1000).toLocaleString() : '从未' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button size="small" @click="showEditDialog(row)">修改等级</el-button>
                <el-button size="small" type="danger" @click="deleteAdmin(row.username)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="权限说明" name="permissions" v-if="!canCustomizeUi">
          <el-alert
            title="权限不足"
            type="warning"
            :closable="false"
          >
            <template #default>
              <p>您的管理员等级为 {{ adminLevel }}，无法访问管理面板</p>
              <p>需要超级管理员(lv4)或更高权限</p>
            </template>
          </el-alert>
        </el-tab-pane>

        <el-tab-pane label="NPC对话管理" name="dialog">
          <el-alert
            title="NPC对话管理"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          >
            <template #default>
              <p>1. 管理各NPC的对话内容和选项</p>
              <p>2. 修改后即时生效</p>
              <p>3. 点击NPC名称可编辑对话</p>
            </template>
          </el-alert>

          <div class="dialog-npc-list">
            <div
              v-for="npc in dialogNpcList"
              :key="npc.npc_id"
              class="dialog-npc-item"
              @click="editNpcDialog(npc)"
            >
              <span class="npc-icon">{{ npc.icon }}</span>
              <div class="npc-info">
                <span class="npc-name">{{ npc.name }}</span>
                <span class="npc-title">{{ npc.title }}</span>
              </div>
              <span class="npc-type">{{ npc.npc_type }}</span>
              <span class="dialog-count">{{ npc.dialog_node_count }} 个对话节点</span>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div class="admin-content" v-else>
      <el-card class="admin-login-card">
        <template #header>
          <span>🔐 管理员登录</span>
        </template>
        <el-form label-width="80px">
          <el-form-item label="账号">
            <el-input v-model="loginForm.username" placeholder="管理员账号" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="loginForm.password" type="password" placeholder="管理员密码" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleLogin" :loading="loginLoading">登录</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <el-dialog v-model="createDialogVisible" title="创建管理员" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createForm.password" type="password" />
        </el-form-item>
        <el-form-item label="等级">
          <el-select v-model="createForm.level">
            <el-option label="观察员 (lv1)" :value="1" />
            <el-option label="版主 (lv2)" :value="2" />
            <el-option label="管理员 (lv3)" :value="3" />
            <el-option label="超级管理员 (lv4)" :value="4" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createAdmin">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="修改管理员等级" width="400px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="新等级">
          <el-select v-model="editForm.level">
            <el-option label="观察员 (lv1)" :value="1" />
            <el-option label="版主 (lv2)" :value="2" />
            <el-option label="管理员 (lv3)" :value="3" />
            <el-option label="超级管理员 (lv4)" :value="4" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="updateAdmin">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="npcDialogVisible" :title="`编辑NPC对话 - ${editingNpc?.name || ''}`" width="800px" top="5vh">
      <div v-if="editingNpc" class="npc-dialog-editor">
        <div class="editor-header">
          <div class="npc-info-row">
            <span class="npc-icon-large">{{ editingNpc.icon }}</span>
            <div>
              <strong>{{ editingNpc.name }}</strong> - {{ editingNpc.title }}
            </div>
          </div>
        </div>

        <el-tabs v-model="dialogEditTab" type="border-card">
          <el-tab-pane label="基本信息" name="basic">
            <el-form label-width="100px">
              <el-form-item label="NPC名称">
                <el-input v-model="editingNpc.name" />
              </el-form-item>
              <el-form-item label="NPC头衔">
                <el-input v-model="editingNpc.title" />
              </el-form-item>
              <el-form-item label="图标">
                <el-input v-model="editingNpc.icon" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="editingNpc.description" type="textarea" :rows="2" />
              </el-form-item>
              <el-form-item label="NPC类型">
                <el-select v-model="editingNpc.npc_type">
                  <el-option label="镇长" value="mayor" />
                  <el-option label="商人" value="merchant" />
                  <el-option label="铁匠" value="blacksmith" />
                  <el-option label="酒馆老板" value="tavern_keeper" />
                  <el-option label="守卫队长" value="guard_captain" />
                  <el-option label="村长" value="village_elder" />
                  <el-option label="村民" value="villager" />
                  <el-option label="马商" value="horse_trader" />
                </el-select>
              </el-form-item>
              <el-form-item label="性格">
                <el-select v-model="editingNpc.personality">
                  <el-option label="友好" value="friendly" />
                  <el-option label="中立" value="neutral" />
                  <el-option label="暴躁" value="grumpy" />
                </el-select>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="对话编辑" name="dialogs">
            <div class="dialog-editor">
              <div class="dialog-node-list">
                <div
                  v-for="(node, nodeId) in editingNpc.dialog"
                  :key="nodeId"
                  class="dialog-node-item"
                  :class="{ active: selectedDialogNode === nodeId }"
                  @click="selectedDialogNode = nodeId"
                >
                  <span class="node-id">{{ nodeId }}</span>
                  <span class="node-text-preview">{{ node.text?.substring(0, 30) || '' }}...</span>
                  <span class="node-option-count">{{ node.options?.length || 0 }} 个选项</span>
                </div>
              </div>

              <div v-if="selectedDialogNode && editingNpc.dialog[selectedDialogNode]" class="dialog-node-editor">
                <h4>编辑对话节点: {{ selectedDialogNode }}</h4>
                <el-form label-width="80px">
                  <el-form-item label="对话文本">
                    <el-input
                      v-model="editingNpc.dialog[selectedDialogNode].text"
                      type="textarea"
                      :rows="3"
                    />
                  </el-form-item>
                  <el-form-item label="对话选项">
                    <div class="dialog-options-editor">
                      <div
                        v-for="(opt, idx) in editingNpc.dialog[selectedDialogNode].options"
                        :key="opt.option_id || idx"
                        class="dialog-option-item"
                      >
                        <div class="option-row">
                          <el-input v-model="opt.text" placeholder="选项文本" size="small" style="flex:1" />
                          <el-input v-model="opt.next_node" placeholder="下一节点" size="small" style="width:150px" />
                          <el-select v-model="opt.action" size="small" style="width:150px">
                            <el-option label="无" value="none" />
                            <el-option label="显示任务" value="show_quests" />
                            <el-option label="显示信息" value="show_info" />
                            <el-option label="打开礼物" value="show_gift_selector" />
                            <el-option label="打开商店" value="open_shop" />
                            <el-option label="打开铁匠" value="open_blacksmith" />
                            <el-option label="休息" value="rest" />
                            <el-option label="关闭" value="close" />
                          </el-select>
                          <el-input-number v-model="opt.min_favor" :min="0" :max="100" size="small" style="width:80px" />
                          <el-button type="danger" size="small" @click="removeDialogOption(selectedDialogNode, idx)">×</el-button>
                        </div>
                      </div>
                      <el-button size="small" @click="addDialogOption(selectedDialogNode)">+ 添加选项</el-button>
                    </div>
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="JSON编辑" name="json">
            <el-input
              v-model="npcDialogJson"
              type="textarea"
              :rows="20"
              placeholder="JSON格式编辑"
              @change="parseNpcDialogJson"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
      <template #footer>
        <el-button @click="npcDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveNpcDialog">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const api = axios.create({
  baseURL: '',
  timeout: 10000
})

const adminToken = ref(localStorage.getItem('qikan_admin_token') || '')
const isAdmin = ref(false)
const adminLevel = ref(0)
const canCustomizeUi = ref(false)
const canManageAdmins = ref(false)
const canUploadIcons = ref(false)
const activeTab = ref('ui')
const loginLoading = ref(false)
const loginForm = ref({ username: '', password: '' })

const uiConfig = ref({
  enabled: false,
  background_color: '#0D0D0D',
  background_gradient_start: '#1A1A1A',
  background_gradient_end: '#151515',
  header_color: '#1A1A1A',
  header_border_color: '#8B0000',
  accent_color: '#D4AF37',
  text_color: '#F5DEB3',
  button_color: '#8B0000'
})

const admins = ref([])
const createDialogVisible = ref(false)
const createForm = ref({ username: '', password: '', level: 2 })
const editDialogVisible = ref(false)
const editForm = ref({ username: '', level: 1 })

const defaultUiConfig = {
  enabled: false,
  background_color: '#0D0D0D',
  background_gradient_start: '#1A1A1A',
  background_gradient_end: '#151515',
  header_color: '#1A1A1A',
  header_border_color: '#8B0000',
  accent_color: '#D4AF37',
  text_color: '#F5DEB3',
  button_color: '#8B0000'
}

async function checkAdminStatus() {
  if (!adminToken.value) {
    isAdmin.value = false
    return
  }
  try {
    const res = await api.post('/api/admin/verify-token', { admin_token: adminToken.value })
    if (res.success) {
      isAdmin.value = res.is_admin
      adminLevel.value = res.level || 0
      canCustomizeUi.value = res.can_customize_ui || false
      canManageAdmins.value = res.can_manage_admins || false
      canUploadIcons.value = res.can_upload_icons || false
      
      if (canCustomizeUi.value) {
        loadUiConfig()
      }
      if (canManageAdmins.value) {
        loadAdmins()
      }
    } else {
      isAdmin.value = false
    }
  } catch (err) {
    isAdmin.value = false
    ElMessage.error('验证失败: ' + (err.message || '网络错误'))
  }
}

async function handleLogin() {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入管理员账号和密码')
    return
  }
  loginLoading.value = true
  try {
    const res = await api.post('/api/admin/login', {
      account: loginForm.value.username,
      password: loginForm.value.password
    })
    if (res.success) {
      adminToken.value = res.admin_token || res.token
      localStorage.setItem('qikan_admin_token', adminToken.value)
      ElMessage.success('登录成功')
      checkAdminStatus()
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch (e) {
    ElMessage.error('登录失败')
  } finally {
    loginLoading.value = false
  }
}

async function loadUiConfig() {
  try {
    const res = await api.post('/api/admin/ui-config', { admin_token: adminToken.value })
    if (res.success) {
      uiConfig.value = { ...uiConfig.value, ...res.config }
    }
  } catch (err) {
    console.error('加载UI配置失败:', err)
  }
}

async function saveUiConfig() {
  try {
    const res = await api.post('/api/admin/ui-config/set', {
      admin_token: adminToken.value,
      config: uiConfig.value
    })
    if (res.success) {
      ElMessage.success('UI配置已保存')
      if (uiConfig.value.enabled) {
        applyUiConfig(uiConfig.value)
      }
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (err) {
    ElMessage.error('保存失败: ' + (err.message || '网络错误'))
  }
}

function resetUiConfig() {
  uiConfig.value = { ...defaultUiConfig }
  saveUiConfig()
}

function applyUiConfig(config) {
  const root = document.documentElement
  root.style.setProperty('--bg-color', config.background_color)
  root.style.setProperty('--bg-gradient-start', config.background_gradient_start)
  root.style.setProperty('--bg-gradient-end', config.background_gradient_end)
  root.style.setProperty('--header-color', config.header_color)
  root.style.setProperty('--header-border', config.header_border_color)
  root.style.setProperty('--accent-color', config.accent_color)
  root.style.setProperty('--text-color', config.text_color)
  root.style.setProperty('--button-color', config.button_color)
}

async function loadAdmins() {
  try {
    const res = await api.post('/api/admin/admins/list', { admin_token: adminToken.value })
    if (res.success) {
      admins.value = res.admins || []
    }
  } catch (err) {
    console.error('加载管理员列表失败:', err)
  }
}

function showCreateDialog() {
  createForm.value = { username: '', password: '', level: 2 }
  createDialogVisible.value = true
}

async function createAdmin() {
  if (!createForm.value.username || !createForm.value.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  try {
    const res = await api.post('/api/admin/admins/create', {
      admin_token: adminToken.value,
      username: createForm.value.username,
      password: createForm.value.password,
      level: createForm.value.level
    })
    if (res.success) {
      ElMessage.success('管理员创建成功')
      createDialogVisible.value = false
      loadAdmins()
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch (err) {
    ElMessage.error('创建失败: ' + (err.message || '网络错误'))
  }
}

function showEditDialog(row) {
  editForm.value = { username: row.username, level: row.level }
  editDialogVisible.value = true
}

async function updateAdmin() {
  try {
    const res = await api.post('/api/admin/admins/update', {
      admin_token: adminToken.value,
      username: editForm.value.username,
      level: editForm.value.level
    })
    if (res.success) {
      ElMessage.success('管理员等级已更新')
      editDialogVisible.value = false
      loadAdmins()
    } else {
      ElMessage.error(res.message || '更新失败')
    }
  } catch (err) {
    ElMessage.error('更新失败: ' + (err.message || '网络错误'))
  }
}

async function deleteAdmin(username) {
  try {
    await ElMessageBox.confirm(`确定要删除管理员 ${username} 吗?`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  
  try {
    const res = await api.post('/api/admin/admins/delete', {
      admin_token: adminToken.value,
      username
    })
    if (res.success) {
      ElMessage.success('管理员已删除')
      loadAdmins()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (err) {
    ElMessage.error('删除失败: ' + (err.message || '网络错误'))
  }
}

function getLevelTagType(level) {
  const types = { 1: 'info', 2: 'warning', 3: 'primary', 4: 'success' }
  return types[level] || 'info'
}

import { ElMessageBox } from 'element-plus'

const dialogNpcList = ref([])
const npcDialogVisible = ref(false)
const editingNpc = ref(null)
const selectedDialogNode = ref('')
const dialogEditTab = ref('basic')
const npcDialogJson = ref('')

async function loadDialogNpcList() {
  try {
    const res = await api.get('/api/admin/dialog-config', {
      headers: { Authorization: `Bearer ${adminToken.value}` }
    })
    if (res.success) {
      dialogNpcList.value = res.npc_list || []
    }
  } catch (err) {
    console.error('加载NPC对话列表失败:', err)
  }
}

function editNpcDialog(npc) {
  const npcData = dialogNpcList.value.find(n => n.npc_id === npc.npc_id)
  if (!npcData) return
  
  api.get('/api/admin/dialog-config', {
    headers: { Authorization: `Bearer ${adminToken.value}` }
  }).then(res => {
    if (res.success && res.config?.npcs?.[npc.npc_id]) {
      const raw = res.config.npcs[npc.npc_id]
      editingNpc.value = { ...raw }
      selectedDialogNode.value = 'greeting'
      dialogEditTab.value = 'basic'
      npcDialogJson.value = JSON.stringify(raw.dialog || {}, null, 2)
      npcDialogVisible.value = true
    } else {
      ElMessage.error('未找到该NPC的对话配置')
    }
  }).catch(err => {
    ElMessage.error('加载失败: ' + (err.message || '网络错误'))
  })
}

function addDialogOption(nodeId) {
  if (!editingNpc.value?.dialog?.[nodeId]) return
  if (!editingNpc.value.dialog[nodeId].options) {
    editingNpc.value.dialog[nodeId].options = []
  }
  const idx = editingNpc.value.dialog[nodeId].options.length + 1
  editingNpc.value.dialog[nodeId].options.push({
    option_id: `opt_custom_${idx}`,
    text: '新选项',
    next_node: 'greeting',
    action: 'none',
    action_data: {},
    min_favor: 0,
  })
}

function removeDialogOption(nodeId, idx) {
  if (!editingNpc.value?.dialog?.[nodeId]) return
  editingNpc.value.dialog[nodeId].options.splice(idx, 1)
}

function parseNpcDialogJson() {
  try {
    const parsed = JSON.parse(npcDialogJson.value)
    if (editingNpc.value) {
      editingNpc.value.dialog = parsed
    }
  } catch (e) {
    console.warn('JSON解析失败:', e)
  }
}

function saveNpcDialog() {
  if (!editingNpc.value) return
  
  const npcData = {
    name: editingNpc.value.name,
    title: editingNpc.value.title,
    icon: editingNpc.value.icon,
    description: editingNpc.value.description,
    npc_type: editingNpc.value.npc_type,
    personality: editingNpc.value.personality,
    dialog: editingNpc.value.dialog,
  }

  api.post('/api/admin/dialog-config/npc', {
    admin_token: adminToken.value,
    npc_id: editingNpc.value.npc_id || '',
    npc_data: npcData,
  }).then(res => {
    if (res.success) {
      ElMessage.success('NPC对话配置已保存')
      npcDialogVisible.value = false
      loadDialogNpcList()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  }).catch(err => {
    ElMessage.error('保存失败: ' + (err.message || '网络错误'))
  })
}

onMounted(() => {
  checkAdminStatus()
  loadDialogNpcList()
})
</script>

<style scoped>
.view-container {
  min-height: 100vh;
  background: linear-gradient(180deg, #0D0D0D 0%, #1A1A1A 50%, #151515 100%);
  color: #F5DEB3;
}

.nav-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 2px solid #8B0000;
}

.nav-bar h2 {
  margin: 0;
  color: #D4AF37;
}

.admin-content {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.ui-config-form {
  background: rgba(0, 0, 0, 0.3);
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #3D3D3D;
}

.color-value {
  margin-left: 12px;
  font-family: monospace;
  color: #888;
}

:deep(.el-form-item__label) {
  color: #F5DEB3;
}

:deep(.el-input__wrapper) {
  background: #0D0D0D;
  border: 1px solid #3D3D3D;
}

:deep(.el-input__inner) {
  color: #F5DEB3;
}

:deep(.el-select) {
  width: 100%;
}

.admin-login-card {
  max-width: 400px;
  margin: 50px auto;
  background: #16213e;
  border: 1px solid #3D3D3D;
}

.admin-login-card :deep(.el-card__header) {
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 1px solid #3D3D3D;
  color: #ffd700;
  font-weight: bold;
}

.dialog-npc-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dialog-npc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.dialog-npc-item:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.dialog-npc-item .npc-icon {
  font-size: 28px;
}

.dialog-npc-item .npc-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.dialog-npc-item .npc-name {
  color: #fff;
  font-weight: 600;
}

.dialog-npc-item .npc-title {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.dialog-npc-item .npc-type {
  padding: 2px 8px;
  background: rgba(74, 158, 255, 0.2);
  color: #4a9eff;
  border-radius: 4px;
  font-size: 12px;
}

.dialog-npc-item .dialog-count {
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
}

.npc-dialog-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.npc-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  color: #fff;
}

.npc-icon-large {
  font-size: 36px;
}

.npc-prefs {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.dialog-editor {
  display: flex;
  gap: 16px;
  min-height: 400px;
}

.dialog-node-list {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 500px;
  overflow-y: auto;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  padding-right: 12px;
}

.dialog-node-item {
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dialog-node-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.dialog-node-item.active {
  background: rgba(74, 158, 255, 0.15);
  border-color: #4a9eff;
}

.dialog-node-item .node-id {
  font-size: 12px;
  font-weight: 600;
  color: #4a9eff;
}

.dialog-node-item .node-text-preview {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog-node-item .node-option-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.dialog-node-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-node-editor h4 {
  color: #fff;
  margin: 0;
  font-size: 14px;
}

.dialog-options-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dialog-option-item {
  padding: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-tabs__content) {
  padding: 16px;
}

:deep(.el-tabs--border-card) {
  background: rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.1);
}

:deep(.el-tabs--border-card > .el-tabs__header) {
  background: rgba(0, 0, 0, 0.3);
  border-bottom-color: rgba(255, 255, 255, 0.1);
}

:deep(.el-tabs__item) {
  color: rgba(255, 255, 255, 0.6);
}

:deep(.el-tabs__item.is-active) {
  color: #4a9eff;
}

:deep(.el-form-item__label) {
  color: rgba(255, 255, 255, 0.8);
}
</style>
