<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>🗺️ 卡拉迪亚大陆</h2>
      <div class="coord-display" v-if="playerLocation">
        📍 当前位置: {{ playerLocation.name }} (X: {{ playerLocation.x }}, Y: {{ playerLocation.y }})
      </div>
    </div>
    
    <div class="map-wrapper">
      <!-- X轴 -->
      <div class="axis axis-x">
        <span class="axis-label" v-for="i in 9" :key="i">{{ (i-1) * 100 }}</span>
      </div>
      
      <div class="map-content">
        <!-- Y轴 -->
        <div class="axis axis-y">
          <span class="axis-label" v-for="i in 7" :key="i">{{ (6-i) * 100 }}</span>
        </div>
        
        <div class="map-canvas" ref="mapRef">
          <!-- 网格线 -->
          <div class="grid-lines">
            <div class="grid-line horizontal" v-for="i in 7" :key="'h'+i"></div>
            <div class="grid-line vertical" v-for="i in 9" :key="'v'+i"></div>
          </div>
          
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
            <span class="marker-coord">({{ loc.x }},{{ loc.y }})</span>
          </div>
          
          <div 
            v-if="playerLocation"
            class="player-marker"
            :style="{ left: playerLocation.x + 'px', top: playerLocation.y + 'px' }"
          >
            👤
            <span class="player-coord">({{ playerLocation.x }},{{ playerLocation.y }})</span>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="detailVisible" :title="selectedLocation?.name" width="400px">
      <div v-if="selectedLocation" class="location-detail">
        <p><strong>坐标:</strong> X: {{ selectedLocation.x }}, Y: {{ selectedLocation.y }}</p>
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

const mapApi = axios.create({
  baseURL: '',
  timeout: 10000
})

mapApi.interceptors.request.use(config => {
  const token = localStorage.getItem('qikan_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

mapApi.interceptors.response.use(
  res => res.data,
  err => {
    ElMessage.error(err.response?.data?.message || '请求失败')
    return Promise.reject(err)
  }
)

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
    await mapApi.post(`/api/map/travel`, { location_id: selectedLocation.value.location_id })
    ElMessage.success('开始旅行...')
    detailVisible.value = false
  } catch (e) {
    ElMessage.error('旅行失败')
  }
}

const loadLocations = async () => {
  try {
    const res = await mapApi.get('/api/map/locations')
    locations.value = res.data.locations || []
    
    const playerRes = await mapApi.get('/api/map/player')
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

.coord-display {
  color: #7ec8e3;
  font-size: 14px;
  background: rgba(0,0,0,0.3);
  padding: 8px 16px;
  border-radius: 8px;
}

.map-wrapper {
  background: #16213e;
  border-radius: 12px;
  padding: 20px;
  overflow: auto;
}

.map-content {
  display: flex;
}

.axis {
  display: flex;
  position: relative;
}

.axis-x {
  margin-left: 30px;
  width: 800px;
  justify-content: space-between;
  padding-bottom: 5px;
}

.axis-y {
  flex-direction: column;
  height: 600px;
  justify-content: space-between;
  padding-right: 5px;
}

.axis-label {
  color: #5a8f7b;
  font-size: 10px;
}

.map-canvas {
  position: relative;
  width: 800px;
  height: 600px;
  background: linear-gradient(180deg, #2d4a3e 0%, #1a2f25 100%);
  border-radius: 8px;
  border: 1px solid #3a5a4a;
}

.grid-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.grid-line {
  position: absolute;
  background: rgba(90, 143, 123, 0.2);
}

.grid-line.horizontal {
  width: 100%;
  height: 1px;
}

.grid-line.horizontal:nth-child(1) { top: 0; }
.grid-line.horizontal:nth-child(2) { top: 16.67%; }
.grid-line.horizontal:nth-child(3) { top: 33.33%; }
.grid-line.horizontal:nth-child(4) { top: 50%; }
.grid-line.horizontal:nth-child(5) { top: 66.67%; }
.grid-line.horizontal:nth-child(6) { top: 83.33%; }
.grid-line.horizontal:nth-child(7) { top: 100%; }

.grid-line.vertical {
  width: 1px;
  height: 100%;
}

.grid-line.vertical:nth-child(8) { left: 0; }
.grid-line.vertical:nth-child(9) { left: 12.5%; }
.grid-line.vertical:nth-child(10) { left: 25%; }
.grid-line.vertical:nth-child(11) { left: 37.5%; }
.grid-line.vertical:nth-child(12) { left: 50%; }
.grid-line.vertical:nth-child(13) { left: 62.5%; }
.grid-line.vertical:nth-child(14) { left: 75%; }
.grid-line.vertical:nth-child(15) { left: 87.5%; }
.grid-line.vertical:nth-child(16) { left: 100%; }

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

.marker-coord {
  font-size: 9px;
  color: #8fbc8f;
  margin-top: 2px;
}

.location-marker.active .marker-icon {
  filter: drop-shadow(0 0 8px #ffd700);
}

.player-marker {
  position: absolute;
  font-size: 24px;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.player-coord {
  font-size: 10px;
  color: #ffd700;
  background: rgba(0,0,0,0.6);
  padding: 2px 4px;
  border-radius: 3px;
  margin-top: 2px;
}

.location-detail p {
  margin: 8px 0;
  color: #e0e0e0;
}
</style>
