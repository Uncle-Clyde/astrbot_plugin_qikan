<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>🏰 家族系统</h2>
    </div>
    
    <!-- 未加入家族 -->
    <el-card v-if="!inFamily" class="create-card">
      <p>你还没有家族</p>
      <el-button type="primary" @click="showCreate = true">创建家族</el-button>
      <el-button @click="loadFamilyList">查看已有家族</el-button>
      
      <el-table v-if="familyList.length > 0" :data="familyList" style="width: 100%; margin-top: 16px" stripe>
        <el-table-column prop="name" label="家族名" />
        <el-table-column prop="member_count" label="成员" width="80" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="joinFamily(row.sect_id)">加入</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 已加入家族 -->
    <el-card v-else class="family-card">
      <template #header>
        <div class="card-header">
          <span>{{ family.name }}</span>
          <div class="header-actions">
            <el-tag>{{ myRole }}</el-tag>
            <el-button size="small" type="danger" @click="leaveFamily" :disabled="myRole === '族长'">离开家族</el-button>
          </div>
        </div>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="概览" name="overview">
          <div class="overview-section">
            <p>描述: {{ family.description || '暂无描述' }}</p>
            <p>成员: {{ members.length }} 人</p>
            <p>等级: {{ family.level || 1 }}</p>
            <p>经验: {{ family.exp || 0 }} / {{ family.exp_next || 100 }}</p>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="成员" name="members">
          <el-table :data="members" style="width: 100%">
            <el-table-column prop="name" label="成员" />
            <el-table-column prop="role_name" label="职位" width="100" />
            <el-table-column prop="contribution_points" label="贡献" width="100" />
            <el-table-column label="操作" width="200" v-if="canManage">
              <template #default="{ row }">
                <el-select v-model="roleChanges[row.user_id]" size="small" placeholder="设置角色" style="width: 120px">
                  <el-option label="族长" value="leader" :disabled="myRole !== '族长'" />
                  <el-option label="长老" value="elder" />
                  <el-option label="成员" value="member" />
                </el-select>
                <el-button size="small" type="primary" @click="setRole(row.user_id)">设置</el-button>
                <el-button size="small" type="danger" @click="kickMember(row.user_id)" :disabled="row.role_name === '族长'">踢出</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="仓库" name="warehouse">
          <div class="warehouse-section">
            <h4>存入物品</h4>
            <el-form inline>
              <el-form-item label="物品">
                <el-select v-model="depositItem" placeholder="选择物品" style="width: 200px">
                  <el-option v-for="item in myInventory" :key="item.item_id" :label="`${item.name} x${item.count}`" :value="item.item_id" />
                </el-select>
              </el-form-item>
              <el-form-item label="数量">
                <el-input-number v-model="depositCount" :min="1" :max="99" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="depositItemToWarehouse">存入</el-button>
              </el-form-item>
            </el-form>
            
            <h4>仓库物品</h4>
            <el-table :data="warehouse" style="width: 100%">
              <el-table-column prop="name" label="物品" />
              <el-table-column prop="count" label="数量" width="100" />
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-input-number v-model="exchangeCounts[row.item_id]" :min="1" :max="row.count" size="small" />
                  <el-button size="small" type="warning" @click="exchangeItem(row.item_id)">取出</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="任务" name="tasks" v-if="myRole !== '成员'">
          <div class="tasks-section">
            <div class="task-header">
              <h4>家族任务</h4>
              <el-button type="primary" size="small" @click="showCreateTask = true" v-if="canManage">创建任务</el-button>
            </div>
            <el-table :data="tasks" style="width: 100%">
              <el-table-column prop="name" label="任务名" />
              <el-table-column prop="description" label="描述" />
              <el-table-column prop="progress" label="进度" width="100" />
              <el-table-column prop="target" label="目标" width="100" />
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-button size="small" type="primary" @click="acceptTask(row.task_id)">接受</el-button>
                  <el-button size="small" type="warning" @click="updateTaskProgress(row.task_id)">更新</el-button>
                  <el-button size="small" type="danger" @click="cancelTask(row.task_id)" v-if="canManage">取消</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="规则" name="rules" v-if="canManage">
          <div class="rules-section">
            <h4>贡献规则</h4>
            <el-form label-width="120px">
              <el-form-item label="提交比例">
                <el-input-number v-model="rules.submit_ratio" :min="1" :max="100" />
                <span style="margin-left: 8px; color: #888">物品价值 → 贡献点</span>
              </el-form-item>
              <el-form-item label="交换比例">
                <el-input-number v-model="rules.exchange_ratio" :min="1" :max="100" />
                <span style="margin-left: 8px; color: #888">贡献点 → 物品价值</span>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="saveRules">保存规则</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- 创建家族对话框 -->
    <el-dialog v-model="showCreate" title="创建家族" width="400px">
      <el-form>
        <el-form-item label="家族名">
          <el-input v-model="createForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :disabled="gameStore.isActionLocked('sect_create')">创建</el-button>
      </template>
    </el-dialog>
    
    <!-- 创建任务对话框 -->
    <el-dialog v-model="showCreateTask" title="创建任务" width="400px">
      <el-form>
        <el-form-item label="任务名">
          <el-input v-model="taskForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="taskForm.description" type="textarea" />
        </el-form-item>
        <el-form-item label="目标数量">
          <el-input-number v-model="taskForm.target" :min="1" :max="9999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateTask = false">取消</el-button>
        <el-button type="primary" @click="createTask">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const gameStore = useGameStore()

const inFamily = ref(false)
const family = ref(null)
const members = ref([])
const warehouse = ref([])
const tasks = ref([])
const familyList = ref([])
const myRole = ref('')
const activeTab = ref('overview')
const showCreate = ref(false)
const showCreateTask = ref(false)
const createForm = ref({ name: '', description: '' })
const taskForm = ref({ name: '', description: '', target: 10 })
const roleChanges = ref({})
const depositItem = ref('')
const depositCount = ref(1)
const exchangeCounts = ref({})
const myInventory = ref([])
const rules = ref({ submit_ratio: 10, exchange_ratio: 10 })

const canManage = computed(() => myRole.value === '族长' || myRole.value === '长老')

const loadFamilyData = async () => {
  try {
    const result = await gameStore.wsCall('sect_my')
    if (result?.success && result.sect) {
      inFamily.value = true
      family.value = result.sect
      members.value = result.members || []
      myRole.value = result.my_role || '成员'
      warehouse.value = result.warehouse || []
      tasks.value = result.tasks || []
      myInventory.value = result.my_inventory || []
      rules.value = result.rules || { submit_ratio: 10, exchange_ratio: 10 }
    } else {
      inFamily.value = false
    }
  } catch (e) {
    console.error('加载家族数据失败', e)
  }
}

const loadFamilyList = async () => {
  try {
    const result = await gameStore.wsCall('sect_list')
    familyList.value = result?.sects || []
  } catch (e) {}
}

const handleCreate = async () => {
  if (!createForm.value.name) {
    ElMessage.warning('请输入家族名')
    return
  }
  try {
    const result = await gameStore.wsCall('sect_create', { name: createForm.value.name, description: createForm.value.description })
    if (result?.success) {
      ElMessage.success('家族创建成功')
      showCreate.value = false
      await loadFamilyData()
    } else {
      ElMessage.error(result?.message || '创建失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

const joinFamily = async (sectId) => {
  try {
    const result = await gameStore.wsCall('sect_join', { sect_id: sectId })
    if (result?.success) {
      ElMessage.success('加入成功')
      await loadFamilyData()
    } else {
      ElMessage.error(result?.message || '加入失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

const leaveFamily = async () => {
  try {
    await ElMessageBox.confirm('确定要离开家族吗？', '确认')
    const result = await gameStore.wsCall('sect_leave')
    if (result?.success) {
      ElMessage.success('已离开家族')
      inFamily.value = false
    }
  } catch (e) {}
}

const setRole = async (userId) => {
  const role = roleChanges.value[userId]
  if (!role) return
  try {
    const result = await gameStore.wsCall('sect_set_role', { user_id: userId, role })
    if (result?.success) {
      ElMessage.success('角色设置成功')
      await loadFamilyData()
    }
  } catch (e) {
    ElMessage.error('设置失败')
  }
}

const kickMember = async (userId) => {
  try {
    await ElMessageBox.confirm('确定要踢出该成员吗？', '确认')
    const result = await gameStore.wsCall('sect_kick', { user_id: userId })
    if (result?.success) {
      ElMessage.success('已踢出')
      await loadFamilyData()
    }
  } catch (e) {}
}

const depositItemToWarehouse = async () => {
  if (!depositItem.value) {
    ElMessage.warning('请选择物品')
    return
  }
  try {
    const result = await gameStore.wsCall('sect_warehouse_deposit', { item_id: depositItem.value, count: depositCount.value })
    if (result?.success) {
      ElMessage.success('存入成功')
      await loadFamilyData()
    }
  } catch (e) {
    ElMessage.error('存入失败')
  }
}

const exchangeItem = async (itemId) => {
  const count = exchangeCounts.value[itemId] || 1
  try {
    const result = await gameStore.wsCall('sect_warehouse_exchange', { item_id: itemId, count })
    if (result?.success) {
      ElMessage.success('取出成功')
      await loadFamilyData()
    }
  } catch (e) {
    ElMessage.error('取出失败')
  }
}

const acceptTask = async (taskId) => {
  try {
    const result = await gameStore.wsCall('sect_accept_task', { task_id: taskId })
    if (result?.success) {
      ElMessage.success('已接受任务')
      await loadFamilyData()
    }
  } catch (e) {}
}

const updateTaskProgress = async (taskId) => {
  try {
    const result = await gameStore.wsCall('sect_update_task_progress', { task_id: taskId, progress: 1 })
    if (result?.success) {
      ElMessage.success('进度已更新')
      await loadFamilyData()
    }
  } catch (e) {}
}

const cancelTask = async (taskId) => {
  try {
    const result = await gameStore.wsCall('sect_cancel_task', { task_id: taskId })
    if (result?.success) {
      ElMessage.success('任务已取消')
      await loadFamilyData()
    }
  } catch (e) {}
}

const createTask = async () => {
  if (!taskForm.value.name) {
    ElMessage.warning('请输入任务名')
    return
  }
  try {
    const result = await gameStore.wsCall('sect_create_task', { name: taskForm.value.name, description: taskForm.value.description, target: taskForm.value.target })
    if (result?.success) {
      ElMessage.success('任务创建成功')
      showCreateTask.value = false
      await loadFamilyData()
    }
  } catch (e) {
    ElMessage.error('创建失败')
  }
}

const saveRules = async () => {
  try {
    await gameStore.wsCall('sect_set_submit_rule', { ratio: rules.value.submit_ratio })
    await gameStore.wsCall('sect_set_exchange_rule', { ratio: rules.value.exchange_ratio })
    ElMessage.success('规则已保存')
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
  await loadFamilyData()
})
</script>

<style scoped>
.view-container { min-height: 100vh; background: #1a1a2e; padding: 20px; }
.nav-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
.nav-bar h2 { color: #ffd700; margin: 0; }
.create-card, .family-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #e0e0e0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.overview-section p { margin: 8px 0; color: #aaa; }
.warehouse-section h4 { color: #d4a464; margin: 16px 0 8px; }
.task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.task-header h4 { color: #d4a464; margin: 0; }
.rules-section h4 { color: #d4a464; margin-bottom: 12px; }
</style>
