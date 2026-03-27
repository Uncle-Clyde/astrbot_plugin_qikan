<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>🏰 家族系统</h2>
    </div>
    
    <el-card v-if="!inFamily" class="create-card">
      <p>你还没有家族</p>
      <el-button type="primary" @click="showCreate = true">创建家族</el-button>
      <el-button @click="loadFamilyList">查看已有家族</el-button>
    </el-card>
    
    <el-card v-else class="family-card">
      <template #header>
        <div class="card-header">
          <span>{{ family.name }}</span>
          <el-tag>{{ myRole }}</el-tag>
        </div>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="成员" name="members">
          <el-table :data="members" style="width: 100%">
            <el-table-column prop="name" label="成员" />
            <el-table-column prop="role_name" label="职位" />
            <el-table-column prop="contribution_points" label="贡献" />
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="仓库" name="warehouse">
          <el-table :data="warehouse" style="width: 100%">
            <el-table-column prop="name" label="物品" />
            <el-table-column prop="count" label="数量" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
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
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'

const gameStore = useGameStore()

const inFamily = ref(false)
const family = ref(null)
const members = ref([])
const warehouse = ref([])
const myRole = ref('')
const activeTab = ref('members')
const showCreate = ref(false)
const createForm = ref({ name: '', description: '' })

const loadFamilyList = () => {
  gameStore.send({ type: 'sect_list' })
}

const handleCreate = async () => {
  gameStore.send({ 
    type: 'sect_create', 
    data: { 
      name: createForm.value.name, 
      description: createForm.value.description 
    } 
  })
  showCreate.value = false
  ElMessage.success('家族创建成功')
}

onMounted(() => {
  gameStore.send({ type: 'sect_my' })
})
</script>

<style scoped>
.view-container { min-height: 100vh; background: #1a1a2e; padding: 20px; }
.nav-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
.nav-bar h2 { color: #ffd700; margin: 0; }
.create-card, .family-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #e0e0e0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
