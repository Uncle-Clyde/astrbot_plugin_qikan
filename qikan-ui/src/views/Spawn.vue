<template>
  <div class="spawn-container">
    <div class="spawn-background">
      <div class="bg-pattern"></div>
    </div>
    
    <div class="spawn-box">
      <div class="header-section">
        <div class="sword-icon">⚔️</div>
        <h1 class="title">选择你的出身</h1>
        <p class="subtitle">卡拉迪亚大陆欢迎你</p>
      </div>
      
      <div class="origin-section">
        <h3>选择出身背景</h3>
        <p class="section-desc">不同的出身将决定你在这片大陆上的起点</p>
        <div v-if="loadingOrigins" class="loading-state">
          <el-icon class="loading-icon"><Loading /></el-icon>
          <span>加载出身数据中...</span>
        </div>
        <div v-else-if="spawnOrigins.length === 0" class="empty-state">
          <el-empty description="无法加载出身数据" />
          <el-button type="primary" @click="loadSpawnData">重新加载</el-button>
          <el-button @click="debugLoad">调试加载</el-button>
        </div>
        <div v-else class="origin-grid">
          <div 
            v-for="origin in spawnOrigins" 
            :key="origin.origin_id"
            class="origin-card"
            :class="{ selected: selectedOrigin === origin.origin_id }"
            @click="selectOrigin(origin.origin_id)"
          >
            <span class="origin-icon">{{ origin.icon }}</span>
            <span class="origin-name">{{ origin.name }}</span>
            <span class="origin-desc">{{ origin.description }}</span>
            <span class="origin-bonus">{{ origin.specialty }}</span>
          </div>
        </div>
      </div>
      
      <div v-if="selectedOrigin" class="location-section">
        <h3>选择出生地点</h3>
        <p class="section-desc">选择你要降临的城镇</p>
        <div v-if="loadingLocations" class="loading-state">
          <el-icon class="loading-icon"><Loading /></el-icon>
          <span>加载地点数据中...</span>
        </div>
        <div v-else-if="filteredLocations.length === 0" class="empty-state">
          <el-empty description="暂无可用地点" />
        </div>
        <div v-else class="location-grid">
          <div 
            v-for="loc in filteredLocations" 
            :key="loc.location_id"
            class="location-card"
            :class="{ selected: selectedLocation === loc.location_id }"
            @click="selectLocation(loc.location_id)"
          >
            <span class="loc-icon">{{ loc.icon }}</span>
            <span class="loc-name">{{ loc.name }}</span>
            <span class="loc-faction">{{ loc.faction_name }}</span>
            <span class="loc-desc">{{ loc.description }}</span>
          </div>
        </div>
      </div>
      
      <div class="action-section">
        <el-button 
          type="primary"
          size="large"
          :loading="loading"
          :disabled="!selectedOrigin"
          @click="confirmSelection"
          class="confirm-btn"
        >
          {{ selectedLocation ? '确认选择' : '请选择出身' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

console.log('[Spawn] Page loaded')

const router = useRouter()
const gameStore = useGameStore()

const loading = ref(false)
const loadingOrigins = ref(true)
const loadingLocations = ref(true)
const spawnOrigins = ref([])
const spawnLocations = ref([])
const selectedOrigin = ref('')
const selectedLocation = ref('')
let spawnTimeoutTimer = null

const filteredLocations = computed(() => {
  if (!selectedOrigin.value) return []
  return spawnLocations.value.filter(loc => 
    loc.available_origins.includes(selectedOrigin.value)
  )
})

const handleWsMessage = (msg) => {
  console.log('Spawn received message:', msg.type)
  if (msg.type === 'spawn_origins') {
    spawnOrigins.value = msg.data || []
    console.log('Loaded origins:', spawnOrigins.value.length)
    loadingOrigins.value = false
  } else if (msg.type === 'spawn_locations') {
    spawnLocations.value = msg.data || []
    console.log('Loaded locations:', spawnLocations.value.length)
    loadingLocations.value = false
  } else if (msg.type === 'action_result' && msg.action === 'set_spawn_origin') {
    if (spawnTimeoutTimer) {
      clearTimeout(spawnTimeoutTimer)
      spawnTimeoutTimer = null
    }
    if (msg.data?.success) {
      ElMessage.success('选择成功！')
      loading.value = false
      gameStore.getPanel()
      gameStore.getInventory()
      router.push('/home')
    } else {
      ElMessage.error(msg.data?.message || '选择失败')
      loading.value = false
    }
  } else if (msg.type === 'error') {
    if (spawnTimeoutTimer) {
      clearTimeout(spawnTimeoutTimer)
      spawnTimeoutTimer = null
    }
    ElMessage.error(msg.message || '服务器发生错误')
    loading.value = false
  }
}

const loadSpawnData = async () => {
  loadingOrigins.value = true
  loadingLocations.value = true
  
  try {
    const token = localStorage.getItem('qikan_token')
    const headers = {
      'Content-Type': 'application/json'
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    const originsRes = await fetch('/api/spawn/origins', {
      method: 'GET',
      headers
    })
    const originsData = await originsRes.json()
    if (originsData.success) {
      spawnOrigins.value = originsData.data || []
    }
    loadingOrigins.value = false
    
    const locationsRes = await fetch('/api/spawn/locations', {
      method: 'GET',
      headers
    })
    const locationsData = await locationsRes.json()
    if (locationsData.success) {
      spawnLocations.value = locationsData.data || []
    }
    loadingLocations.value = false
    
  } catch (e) {
    console.error('HTTP load failed, fallback to WebSocket:', e)
    if (!gameStore.connected) {
      await gameStore.connectWs()
      await new Promise(resolve => setTimeout(resolve, 500))
    }
    
    gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
    gameStore.wsMessageHandlers['spawn'] = handleWsMessage
    
    gameStore.send({ type: 'get_spawn_origins' })
    gameStore.send({ type: 'get_spawn_locations' })
    
    setTimeout(() => {
      if (loadingOrigins.value && spawnOrigins.value.length === 0) {
        loadingOrigins.value = false
        ElMessage.warning('获取出身数据超时')
      }
      if (loadingLocations.value && spawnLocations.value.length === 0) {
        loadingLocations.value = false
        ElMessage.warning('获取地点数据超时')
      }
    }, 10000)
  }
}

const debugLoad = async () => {
  console.log('Debug loading spawn data...')
  loadingOrigins.value = true
  loadingLocations.value = true
  
  if (!gameStore.connected) {
    await gameStore.connectWs()
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  
  try {
    console.log('Using sendWithTimeout for origins...')
    const originsRes = await gameStore.sendWithTimeout({ type: 'get_spawn_origins' }, 'origins_debug')
    console.log('Origins response:', originsRes)
    if (originsRes?.type === 'spawn_origins') {
      spawnOrigins.value = originsRes.data || []
      loadingOrigins.value = false
    }
  } catch (e) {
    console.error('Failed to load origins:', e)
    loadingOrigins.value = false
  }
  
  try {
    console.log('Using sendWithTimeout for locations...')
    const locationsRes = await gameStore.sendWithTimeout({ type: 'get_spawn_locations' }, 'locations_debug')
    console.log('Locations response:', locationsRes)
    if (locationsRes?.type === 'spawn_locations') {
      spawnLocations.value = locationsRes.data || []
      loadingLocations.value = false
    }
  } catch (e) {
    console.error('Failed to load locations:', e)
    loadingLocations.value = false
  }
}

const selectOrigin = (originId) => {
  selectedOrigin.value = originId
  selectedLocation.value = ''
}

const selectLocation = (locationId) => {
  selectedLocation.value = locationId
}

const confirmSelection = async () => {
  if (!selectedOrigin.value) {
    ElMessage.warning('请选择出身背景')
    return
  }
  
  if (!gameStore.connected) {
    ElMessage.warning('未连接到服务器，请刷新页面重试')
    return
  }
  
  loading.value = true
  
  if (spawnTimeoutTimer) {
    clearTimeout(spawnTimeoutTimer)
  }
  spawnTimeoutTimer = setTimeout(() => {
    spawnTimeoutTimer = null
    loading.value = false
    ElMessage.error('操作超时，请检查网络连接后重试')
  }, 15000)
  
  gameStore.send({ 
    type: 'set_spawn_origin',
    data: {
      origin: selectedOrigin.value,
      location: selectedLocation.value
    }
  })
}

onMounted(() => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  loadSpawnData()
})

onUnmounted(() => {
  if (spawnTimeoutTimer) {
    clearTimeout(spawnTimeoutTimer)
    spawnTimeoutTimer = null
  }
  if (gameStore.wsMessageHandlers && gameStore.wsMessageHandlers['spawn']) {
    delete gameStore.wsMessageHandlers['spawn']
  }
})

const handleWsMessage = (msg) => {
  console.log('Spawn received message:', msg.type)
  if (msg.type === 'spawn_origins') {
    spawnOrigins.value = msg.data || []
    console.log('Loaded origins:', spawnOrigins.value.length)
    loadingOrigins.value = false
  } else if (msg.type === 'spawn_locations') {
    spawnLocations.value = msg.data || []
    console.log('Loaded locations:', spawnLocations.value.length)
    loadingLocations.value = false
  } else if (msg.type === 'action_result' && msg.action === 'set_spawn_origin') {
    if (spawnTimeoutTimer) {
      clearTimeout(spawnTimeoutTimer)
      spawnTimeoutTimer = null
    }
    if (msg.data?.success) {
      ElMessage.success('选择成功！')
      loading.value = false
      gameStore.getPanel()
      gameStore.getInventory()
      router.push('/home')
    } else {
      ElMessage.error(msg.data?.message || '选择失败')
      loading.value = false
    }
  } else if (msg.type === 'error') {
    if (spawnTimeoutTimer) {
      clearTimeout(spawnTimeoutTimer)
      spawnTimeoutTimer = null
    }
    ElMessage.error(msg.message || '服务器发生错误')
    loading.value = false
  }
}

const loadSpawnData = async () => {
  loadingOrigins.value = true
  loadingLocations.value = true
  
  try {
    const token = localStorage.getItem('qikan_token')
    const headers = {
      'Content-Type': 'application/json'
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    const originsRes = await fetch('/api/spawn/origins', {
      method: 'GET',
      headers
    })
    const originsData = await originsRes.json()
    if (originsData.success) {
      spawnOrigins.value = originsData.data || []
    }
    loadingOrigins.value = false
    
    const locationsRes = await fetch('/api/spawn/locations', {
      method: 'GET',
      headers
    })
    const locationsData = await locationsRes.json()
    if (locationsData.success) {
      spawnLocations.value = locationsData.data || []
    }
    loadingLocations.value = false
    
  } catch (e) {
    console.error('HTTP load failed, fallback to WebSocket:', e)
    if (!gameStore.connected) {
      await gameStore.connectWs()
      await new Promise(resolve => setTimeout(resolve, 500))
    }
    
    gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
    gameStore.wsMessageHandlers['spawn'] = handleWsMessage
    
    gameStore.send({ type: 'get_spawn_origins' })
    gameStore.send({ type: 'get_spawn_locations' })
    
    setTimeout(() => {
      if (loadingOrigins.value && spawnOrigins.value.length === 0) {
        loadingOrigins.value = false
        ElMessage.warning('获取出身数据超时')
      }
      if (loadingLocations.value && spawnLocations.value.length === 0) {
        loadingLocations.value = false
        ElMessage.warning('获取地点数据超时')
      }
    }, 10000)
  }
}

const debugLoad = async () => {
  console.log('Debug loading spawn data...')
  loadingOrigins.value = true
  loadingLocations.value = true
  
  if (!gameStore.connected) {
    await gameStore.connectWs()
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  
  try {
    console.log('Using sendWithTimeout for origins...')
    const originsRes = await gameStore.sendWithTimeout({ type: 'get_spawn_origins' }, 'origins_debug')
    console.log('Origins response:', originsRes)
    if (originsRes?.type === 'spawn_origins') {
      spawnOrigins.value = originsRes.data || []
      loadingOrigins.value = false
    }
  } catch (e) {
    console.error('Failed to load origins:', e)
    loadingOrigins.value = false
  }
  
  try {
    console.log('Using sendWithTimeout for locations...')
    const locationsRes = await gameStore.sendWithTimeout({ type: 'get_spawn_locations' }, 'locations_debug')
    console.log('Locations response:', locationsRes)
    if (locationsRes?.type === 'spawn_locations') {
      spawnLocations.value = locationsRes.data || []
      loadingLocations.value = false
    }
  } catch (e) {
    console.error('Failed to load locations:', e)
    loadingLocations.value = false
  }
}

const selectOrigin = (originId) => {
  selectedOrigin.value = originId
  selectedLocation.value = ''
}

const selectLocation = (locationId) => {
  selectedLocation.value = locationId
}

const confirmSelection = async () => {
  if (!selectedOrigin.value) {
    ElMessage.warning('请选择出身背景')
    return
  }
  
  if (!gameStore.connected) {
    ElMessage.warning('未连接到服务器，请刷新页面重试')
    return
  }
  
  loading.value = true
  
  if (spawnTimeoutTimer) {
    clearTimeout(spawnTimeoutTimer)
  }
  spawnTimeoutTimer = setTimeout(() => {
    spawnTimeoutTimer = null
    loading.value = false
    ElMessage.error('操作超时，请检查网络连接后重试')
  }, 15000)
  
  gameStore.send({ 
    type: 'set_spawn_origin',
    data: {
      origin: selectedOrigin.value,
      location: selectedLocation.value
    }
  })
}

onMounted(() => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  loadSpawnData()
})

onUnmounted(() => {
  if (spawnTimeoutTimer) {
    clearTimeout(spawnTimeoutTimer)
    spawnTimeoutTimer = null
  }
  if (gameStore.wsMessageHandlers && gameStore.wsMessageHandlers['spawn']) {
    delete gameStore.wsMessageHandlers['spawn']
  }
})
</script>

<style scoped>
.spawn-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow-y: auto;
  padding: 20px;
}

.spawn-background {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #0D0D0D 0%, #1A1A1A 50%, #0D0D0D 100%);
  z-index: 0;
}

.bg-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 25% 25%, rgba(139, 0, 0, 0.15) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(212, 175, 55, 0.1) 0%, transparent 50%),
    url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%233D3D3D' fill-opacity='0.1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}

.spawn-box {
  position: relative;
  z-index: 1;
  width: 900px;
  max-width: 100%;
  padding: 32px;
  background: linear-gradient(145deg, rgba(30, 30, 30, 0.95) 0%, rgba(20, 20, 20, 0.98) 100%);
  border-radius: 16px;
  border: 2px solid #3D3D3D;
  box-shadow: 
    0 0 60px rgba(0, 0, 0, 0.8),
    0 0 40px rgba(139, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.header-section {
  text-align: center;
  margin-bottom: 24px;
}

.sword-icon {
  font-size: 48px;
  margin-bottom: 8px;
  filter: drop-shadow(0 0 20px rgba(212, 175, 55, 0.5));
}

.title {
  color: #FFD700;
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: bold;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.8);
}

.subtitle {
  color: #8B7355;
  margin: 0;
  font-size: 14px;
}

.origin-section, .location-section {
  margin-bottom: 24px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #888;
}

.loading-icon {
  font-size: 32px;
  color: #D4AF37;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.origin-section h3, .location-section h3 {
  color: #FFD700;
  font-size: 18px;
  margin: 0 0 8px;
  text-align: center;
}

.section-desc {
  color: #888;
  font-size: 13px;
  text-align: center;
  margin: 0 0 16px;
}

.origin-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.origin-card {
  text-align: center;
  padding: 16px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid #3D3D3D;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.origin-card:hover {
  border-color: #D4AF37;
  background: rgba(212, 175, 55, 0.1);
  transform: translateY(-4px);
}

.origin-card.selected {
  border-color: #FFD700;
  background: rgba(255, 215, 0, 0.15);
  box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
}

.origin-icon {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}

.origin-name {
  color: #F5DEB3;
  font-size: 16px;
  font-weight: bold;
  display: block;
}

.origin-desc {
  color: #888;
  font-size: 12px;
  display: block;
  margin: 8px 0;
  line-height: 1.4;
}

.origin-bonus {
  color: #4CAF50;
  font-size: 12px;
  font-weight: bold;
  display: block;
  background: rgba(76, 175, 80, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
}

.location-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.location-card {
  text-align: center;
  padding: 12px 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid #3D3D3D;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.location-card:hover {
  border-color: #D4AF37;
  background: rgba(212, 175, 55, 0.1);
}

.location-card.selected {
  border-color: #FFD700;
  background: rgba(255, 215, 0, 0.15);
}

.loc-icon {
  font-size: 28px;
  display: block;
}

.loc-name {
  color: #F5DEB3;
  font-size: 14px;
  font-weight: bold;
  display: block;
  margin-top: 4px;
}

.loc-faction {
  color: #8B7355;
  font-size: 11px;
  display: block;
  margin-top: 2px;
}

.loc-desc {
  color: #666;
  font-size: 10px;
  display: block;
  margin-top: 4px;
  line-height: 1.3;
}

.action-section {
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid #3D3D3D;
}

.confirm-btn {
  width: 200px;
  height: 48px;
  font-size: 16px;
  font-weight: bold;
  background: linear-gradient(145deg, #8B0000 0%, #5C0000 100%);
  border: 1px solid #B22222;
}

.confirm-btn:hover:not(:disabled) {
  background: linear-gradient(145deg, #B22222 0%, #8B0000 100%);
  box-shadow: 0 4px 20px rgba(139, 0, 0, 0.5);
}

.confirm-btn:disabled {
  background: #3D3D3D;
  border-color: #4D4D4D;
}

@media (max-width: 768px) {
  .origin-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .location-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .spawn-box {
    padding: 20px;
  }
}
</style>
