<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>⚒️ 铁匠铺</h2>
      <el-button @click="loadConfigs">🔄 刷新</el-button>
    </div>
    
    <div class="blacksmith-content">
      <el-alert
        title="装备强化说明"
        type="info"
        :closable="false"
        style="margin-bottom: 15px"
      >
        强化装备可提升属性，强化有成功概率，失败不返还材料。
      </el-alert>
      
      <el-card class="enhance-card">
        <h3>选择装备类型</h3>
        <el-radio-group v-model="selectedType">
          <el-radio-button v-for="type in equipmentTypes" :key="type" :value="type">
            {{ type }}
          </el-radio-button>
        </el-radio-group>
        
        <div v-if="selectedType" class="current-level">
          <h4>当前强化等级：{{ currentLevel }}</h4>
        </div>
        
        <div v-if="nextConfig" class="enhance-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="成功率">
              <el-tag type="success">{{ (nextConfig.success_rate * 100).toFixed(0) }}%</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="消耗第纳尔">
              <el-tag type="warning">{{ nextConfig.cost_stones }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="攻击加成" v-if="nextConfig.bonus_attack">
              +{{ nextConfig.bonus_attack }}
            </el-descriptions-item>
            <el-descriptions-item label="防御加成" v-if="nextConfig.bonus_defense">
              +{{ nextConfig.bonus_defense }}
            </el-descriptions-item>
            <el-descriptions-item label="生命加成" v-if="nextConfig.bonus_hp">
              +{{ nextConfig.bonus_hp }}
            </el-descriptions-item>
          </el-descriptions>
          
          <div class="enhance-actions">
            <el-button 
              type="primary" 
              size="large"
              @click="doEnhance"
              :disabled="playerSpiritStones < nextConfig.cost_stones"
              :loading="enhancing"
            >
              强化 (+{{ currentLevel + 1 }})
            </el-button>
          </div>
          
          <div class="player-spirit-stones">
            当前第纳尔: <el-tag type="warning">{{ playerSpiritStones }}</el-tag>
          </div>
        </div>
        
        <div v-else-if="selectedType" class="max-level">
          <el-alert title="已达最高强化等级" type="success" :closable="false" />
        </div>
      </el-card>
      
      <el-card class="history-card">
        <h3>强化历史</h3>
        <el-table :data="history" size="small" max-height="200">
          <el-table-column prop="equipment_type" label="装备" />
          <el-table-column prop="from_level" label="从" />
          <el-table-column prop="to_level" label="到" />
          <el-table-column prop="success" label="结果">
            <template #default="{ row }">
              <el-tag :type="row.success ? 'success' : 'danger'">
                {{ row.success ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="cost_stones" label="消耗" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const gameStore = useGameStore()

const equipmentTypes = ['武器', '护甲', '头盔', '鞋子']
const selectedType = ref('武器')
const currentLevel = ref(0)
const configs = ref([])
const enhancing = ref(false)
const history = ref([])

const playerSpiritStones = computed(() => gameStore.player?.spirit_stones || 0)

const nextConfig = computed(() => {
  return configs.value.find(c => c.equipment_type === selectedType.value && c.level === currentLevel.value + 1)
})

const loadConfigs = async () => {
  try {
    const res = await axios.get('/api/blacksmith/configs')
    if (res.data.success) {
      configs.value = res.data.configs || []
    }
  } catch (e) {
    ElMessage.error('加载配置失败')
  }
}

const doEnhance = async () => {
  if (!gameStore.lockAction('enhance')) {
    ElMessage.warning('操作太频繁')
    return
  }
  
  enhancing.value = true
  try {
    const res = await axios.post(`/api/blacksmith/enhance?user_id=${gameStore.userId}&equipment_type=${selectedType.value}&current_level=${currentLevel.value}`)
    if (res.data.success) {
      if (res.data.success_flag) {
        ElMessage.success(`强化成功！等级提升到 ${res.data.new_level}`)
        currentLevel.value = res.data.new_level
      } else {
        ElMessage.error('强化失败，请重试')
      }
      gameStore.player.spirit_stones = playerSpiritStones.value - res.data.cost
    } else {
      ElMessage.error(res.data.message || '强化失败')
    }
  } catch (e) {
    ElMessage.error('强化失败')
  } finally {
    enhancing.value = false
    setTimeout(() => gameStore.unlockAction('enhance'), 1000)
  }
}

onMounted(async () => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  loadConfigs()
})
</script>

<style scoped>
.blacksmith-content {
  padding: 10px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}
.enhance-card, .history-card {
  margin-bottom: 15px;
}
.current-level {
  margin: 20px 0;
}
.enhance-info {
  margin-top: 20px;
}
.enhance-actions {
  margin-top: 20px;
  text-align: center;
}
.player-spirit-stones {
  margin-top: 10px;
  text-align: center;
  font-size: 14px;
}
.max-level {
  margin-top: 20px;
}
</style>
