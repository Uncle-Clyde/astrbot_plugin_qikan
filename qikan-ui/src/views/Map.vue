<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>🗺️ 卡拉迪亚大陆</h2>
    </div>
    
    <div class="map-wrapper">
      <div class="map-canvas" ref="mapRef">
        <div 
          v-for="loc in locations" 
          :key="loc.location_id"
          class="location-marker"
          :class="[loc.type, { active: loc.location_id === currentLocation }]"
          :style="{ left: loc.x + 'px', top: loc.y + 'px' }"
          @click="selectLocation(loc)"
        >
          <span class="marker-icon">{{ getMarkerIcon(loc.type) }}</span>
          <span class="marker-name">{{ loc.name }}</span>
        </div>
        
        <div 
          v-if="playerLocation"
          class="player-marker"
          :style="{ left: playerLocation.x + 'px', top: playerLocation.y + 'px' }"
        >
          👤
        </div>
      </div>
    </div>

    <el-dialog v-model="detailVisible" :title="selectedLocation?.name" width="400px">
      <div v-if="selectedLocation" class="location-detail">
        <p><strong>类型:</strong> {{ getLocationTypeName(selectedLocation.type) }}</p>
        <p><strong>描述:</strong> {{ selectedLocation.description }}</p>
        <p v-if="selectedLocation.faction"><strong>阵营:</strong> {{ selectedLocation.faction }}</p>
        <p v-if="selectedLocation.favor !== undefined"><strong>好感度:</strong> {{ selectedLocation.favor }}</p>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleTravel" :disabled="!canTravel">
          🚶 前往此处
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useGameStore } from '../stores/game'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const gameStore = useGameStore()

const mapRef = ref(null)
const locations = ref([])
const currentLocation = ref('')
const selectedLocation = ref(null)
const detailVisible = ref(false)
const playerLocation = ref(null)

const getMarkerIcon = (type) => {
  const icons = { town: '🏰', castle: '⚔️', village: '🏘️', bandit: '⛺' }
  return icons[type] || '📍'
}

const getLocationTypeName = (type) => {
  const names = { town: '城镇', castle: '城堡', village: '村庄', bandit: '匪窝' }
  return names[type] || '未知'
}

const canTravel = () => {
  return selectedLocation.value && selectedLocation.value.location_id !== currentLocation.value
}

const selectLocation = (loc) => {
  selectedLocation.value = loc
  detailVisible.value = true
}

const handleTravel = async () => {
  if (!selectedLocation.value) return
  try {
    await axios.post(`/api/map/travel`, { location_id: selectedLocation.value.location_id })
    ElMessage.success('开始旅行...')
    detailVisible.value = false
  } catch (e) {
    ElMessage.error('旅行失败')
  }
}

const loadLocations = async () => {
  try {
    const res = await axios.get('/api/map/locations')
    locations.value = res.data.locations || []
    
    const playerRes = await axios.get('/api/map/player')
    currentLocation.value = playerRes.data.location_id
    playerLocation.value = locations.value.find(l => l.location_id === currentLocation.value)
  } catch (e) {
    ElMessage.error('加载地图失败')
  }
}

onMounted(() => {
  loadLocations()
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

.map-wrapper {
  background: #16213e;
  border-radius: 12px;
  padding: 20px;
  overflow: auto;
}

.map-canvas {
  position: relative;
  width: 800px;
  height: 600px;
  background: linear-gradient(180deg, #2d4a3e 0%, #1a2f25 100%);
  border-radius: 8px;
}

.location-marker {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transform: translate(-50%, -50%);
}

.location-marker:hover {
  transform: translate(-50%, -50%) scale(1.1);
}

.marker-icon {
  font-size: 28px;
}

.marker-name {
  font-size: 11px;
  color: #fff;
  background: rgba(0,0,0,0.5);
  padding: 2px 6px;
  border-radius: 4px;
}

.location-marker.active .marker-icon {
  filter: drop-shadow(0 0 8px #ffd700);
}

.player-marker {
  position: absolute;
  font-size: 24px;
  transform: translate(-50%, -50%);
}

.location-detail p {
  margin: 8px 0;
  color: #e0e0e0;
}
</style>
