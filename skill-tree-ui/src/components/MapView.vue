<template>
  <div class="map-container">
    <div class="map-header">
      <h2>🗺️ 卡拉迪亚大陆</h2>
      <div class="map-legend">
        <span class="legend-item">
          <span class="icon town"></span> 城镇
        </span>
        <span class="legend-item">
          <span class="icon castle"></span> 城堡
        </span>
        <span class="legend-item">
          <span class="icon village"></span> 村庄
        </span>
        <span class="legend-item">
          <span class="icon bandit"></span> 匪窝
        </span>
      </div>
    </div>
    
    <div class="map-viewport" ref="mapViewport" @wheel="handleWheel">
      <svg 
        class="map-svg" 
        :viewBox="`0 0 1000 800`"
        @click="handleMapClick"
      >
        <!-- 地图背景 -->
        <defs>
          <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#2a3a4e" stroke-width="0.5" opacity="0.3"/>
          </pattern>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <rect width="1000" height="800" fill="#1a1a2e"/>
        <rect width="1000" height="800" fill="url(#grid)"/>
        
        <!-- 地形装饰 -->
        <g class="terrain">
          <ellipse cx="200" cy="700" rx="150" ry="80" fill="#3d2914" opacity="0.4"/>
          <ellipse cx="800" cy="400" rx="200" ry="100" fill="#2d4a1c" opacity="0.3"/>
          <ellipse cx="500" cy="200" rx="300" ry="120" fill="#4a3728" opacity="0.3"/>
          <ellipse cx="650" cy="650" rx="100" ry="60" fill="#3d5a3d" opacity="0.3"/>
        </g>
        
        <!-- 地点标记 -->
        <g v-for="location in locations" :key="location.location_id" class="location-marker">
          <!-- 连接线（旅行中） -->
          <line 
            v-if="isTraveling && location.location_id === playerState.travel_destination"
            :x1="playerState.x" 
            :y1="playerState.y" 
            :x2="location.x" 
            :y2="location.y"
            stroke="#fbbf24" 
            stroke-width="2" 
            stroke-dasharray="5,5"
            class="travel-line"
          />
          
          <!-- 地点图标 -->
          <g 
            :transform="`translate(${location.x}, ${location.y})`"
            @click.stop="selectLocation(location)"
            class="location-icon"
            :class="{ 
              'selected': selectedLocation?.location_id === location.location_id,
              'player-here': playerState.current_location === location.location_id,
              'nearby': isNearby(location)
            }"
          >
            <!-- 城镇 -->
            <circle 
              v-if="location.location_type === 1"
              r="20" 
              fill="#4a9eff" 
              stroke="#fff" 
              stroke-width="2"
              class="town-marker"
            />
            <text v-if="location.location_type === 1" text-anchor="middle" dy="5" fill="#fff" font-size="16">🏰</text>
            
            <!-- 城堡 -->
            <circle 
              v-if="location.location_type === 2"
              r="18" 
              fill="#ef4444" 
              stroke="#fff" 
              stroke-width="2"
              class="castle-marker"
            />
            <text v-if="location.location_type === 2" text-anchor="middle" dy="5" fill="#fff" font-size="14">⚔️</text>
            
            <!-- 村庄 -->
            <circle 
              v-if="location.location_type === 0"
              r="12" 
              fill="#22c55e" 
              stroke="#fff" 
              stroke-width="1.5"
              class="village-marker"
            />
            <text v-if="location.location_type === 0" text-anchor="middle" dy="4" fill="#fff" font-size="10">🏠</text>
            
            <!-- 匪窝 -->
            <circle 
              v-if="location.location_type === 3"
              r="14" 
              fill="#dc2626" 
              stroke="#fbbf24" 
              stroke-width="2"
              class="bandit-marker"
            />
            <text v-if="location.location_type === 3" text-anchor="middle" dy="5" fill="#fbbf24" font-size="12">☠️</text>
            
            <!-- 地点名称 -->
            <text 
              :y="location.location_type === 1 ? 35 : location.location_type === 0 ? 25 : 30"
              text-anchor="middle" 
              fill="#fff" 
              font-size="10"
              class="location-name"
            >{{ location.name }}</text>
          </g>
        </g>
        
        <!-- 劫匪标记 -->
        <g v-for="bandit in bandits" :key="bandit.bandit_id" class="bandit-marker-group">
          <g 
            :transform="`translate(${bandit.x}, ${bandit.y})`"
            @click.stop="selectBandit(bandit)"
            class="bandit-icon"
            :class="{ 
              'defeated': bandit.is_defeated,
              'selected': selectedBandit?.bandit_id === bandit.bandit_id,
              'low-hp': !bandit.is_defeated && bandit.hp < bandit.max_hp * 0.3
            }"
          >
            <!-- 劫匪图标 -->
            <circle 
              r="12" 
              :fill="bandit.is_defeated ? '#555' : getBanditColor(bandit.level)" 
              :stroke="bandit.is_defeated ? '#333' : '#fbbf24'" 
              stroke-width="2"
              :opacity="bandit.is_defeated ? 0.5 : 1"
            />
            <text 
              text-anchor="middle" 
              dy="4" 
              fill="#fff" 
              font-size="12"
              :opacity="bandit.is_defeated ? 0.5 : 1"
            >{{ bandit.icon }}</text>
            
            <!-- 血条 -->
            <g v-if="!bandit.is_defeated && bandit.hp < bandit.max_hp">
              <rect x="-15" y="-22" width="30" height="4" fill="#333" rx="2"/>
              <rect 
                x="-15" 
                y="-22" 
                :width="30 * (bandit.hp / bandit.max_hp)" 
                height="4" 
                fill="#ef4444" 
                rx="2"
              />
            </g>
            
            <!-- 等级标签 -->
            <text 
              :y="bandit.is_defeated ? 22 : 20"
              text-anchor="middle" 
              fill="#fff" 
              font-size="8"
              :opacity="bandit.is_defeated ? 0.5 : 0.8"
            >Lv.{{ bandit.level }}</text>
          </g>
        </g>
        
        <!-- 玩家位置 -->
        <g v-if="!isTraveling" :transform="`translate(${playerState.x}, ${playerState.y})`" class="player-marker">
          <circle r="15" fill="#fbbf24" stroke="#fff" stroke-width="3" filter="url(#glow)"/>
          <text text-anchor="middle" dy="5" fill="#000" font-size="14" font-weight="bold">★</text>
        </g>
        
        <!-- 旅行指示器 -->
        <g v-if="isTraveling" :transform="`translate(${travelIndicatorX}, ${travelIndicatorY})`" class="travel-indicator">
          <circle r="10" fill="#fbbf24" opacity="0.7">
            <animate attributeName="opacity" values="0.7;1;0.7" dur="1s" repeatCount="indefinite"/>
          </circle>
          <text text-anchor="middle" dy="4" fill="#000" font-size="10">→</text>
        </g>
      </svg>
    </div>
    
    <!-- 位置详情面板 -->
    <div v-if="selectedLocation" class="location-panel">
      <div class="panel-header">
        <h3>{{ selectedLocation.name }}</h3>
        <span class="location-type-badge" :class="getLocationTypeClass(selectedLocation.location_type)">
          {{ getLocationTypeName(selectedLocation.location_type) }}
        </span>
        <button class="close-btn" @click="selectedLocation = null">×</button>
      </div>
      
      <div class="panel-content">
        <p class="location-desc">{{ selectedLocation.description }}</p>
        
        <div class="location-stats">
          <div class="stat">
            <span class="label">所属势力</span>
            <span class="value faction" :style="{ color: getFactionColor(selectedLocation.faction) }">
              {{ selectedLocation.faction_name }}
            </span>
          </div>
          <div class="stat" v-if="selectedLocation.location_type === 0">
            <span class="label">繁荣度</span>
            <span class="value">{{ selectedLocation.prosperity }}%</span>
          </div>
          <div class="stat" v-if="selectedLocation.location_type === 0">
            <span class="label">产出</span>
            <span class="value">{{ selectedLocation.production || '无' }}</span>
          </div>
          <div class="stat" v-if="selectedLocation.location_type === 2">
            <span class="label">守军</span>
            <span class="value">{{ selectedLocation.garrison_size }} 人</span>
          </div>
        </div>
        
        <div class="location-actions">
          <button 
            v-if="canTravelTo(selectedLocation)"
            class="action-btn travel"
            @click="travelTo(selectedLocation)"
          >
            前往此地 ({{ getTravelTime(selectedLocation) }}秒)
          </button>
          <button 
            v-if="canGetQuest(selectedLocation)"
            class="action-btn quest"
            @click="getQuest(selectedLocation)"
          >
            领取任务
          </button>
          <button 
            v-if="canTrade(selectedLocation)"
            class="action-btn trade"
            @click="openTrade(selectedLocation)"
          >
            交易
          </button>
          <button 
            v-if="canBattle(selectedLocation)"
            class="action-btn battle"
            @click="startBattle(selectedLocation)"
          >
            挑战 ({{ selectedLocation.difficulty }}星)
          </button>
          <button 
            v-if="selectedLocation.location_id === playerState.current_location"
            class="action-btn current"
            disabled
          >
            当前位置
          </button>
        </div>
      </div>
    </div>
    
    <!-- 劫匪详情面板 -->
    <div v-if="selectedBandit" class="location-panel bandit-panel">
      <div class="panel-header">
        <h3>{{ selectedBandit.icon }} {{ selectedBandit.name }}</h3>
        <span class="location-type-badge bandit">
          {{ selectedBandit.type }}
        </span>
        <button class="close-btn" @click="selectedBandit = null">×</button>
      </div>
      
      <div class="panel-content">
        <div class="bandit-status" v-if="selectedBandit.is_defeated">
          <p class="defeated-text">☠️ 此劫匪已被击败</p>
          <p class="respawn-text" v-if="selectedBandit.defeated_time_remaining > 0">
            {{ Math.ceil(selectedBandit.defeated_time_remaining / 60) }}分钟后复活
          </p>
        </div>
        
        <div class="bandit-stats">
          <div class="stat">
            <span class="label">等级</span>
            <span class="value level" :class="`level-${Math.ceil(selectedBandit.level / 3)}`">
              Lv.{{ selectedBandit.level }}
            </span>
          </div>
          <div class="stat">
            <span class="label">人数</span>
            <span class="value">{{ selectedBandit.member_count }} 人</span>
          </div>
          <div class="stat">
            <span class="label">距离</span>
            <span class="value">{{ getBanditDistance(selectedBandit) }}</span>
          </div>
        </div>
        
        <div class="hp-bar-container">
          <div class="hp-bar">
            <div class="hp-fill" :style="{ width: `${(selectedBandit.hp / selectedBandit.max_hp) * 100}%` }"></div>
          </div>
          <span class="hp-text">{{ selectedBandit.hp }} / {{ selectedBandit.max_hp }}</span>
        </div>
        
        <div class="bandit-rewards">
          <h4>击败奖励</h4>
          <div class="reward-item">
            <span class="reward-icon">✨</span>
            <span class="reward-label">经验</span>
            <span class="reward-value">{{ Math.round(selectedBandit.max_hp * 0.5) }}</span>
          </div>
          <div class="reward-item">
            <span class="reward-icon">💰</span>
            <span class="reward-label">金币</span>
            <span class="reward-value">{{ Math.round(selectedBandit.max_hp * 0.3) }}</span>
          </div>
        </div>
        
        <div class="location-actions">
          <button 
            v-if="!selectedBandit.is_defeated"
            class="action-btn attack"
            @click="attackBandit(selectedBandit)"
          >
            ⚔️ 攻击劫匪
          </button>
          <p v-else class="waiting-text">
            请等待劫匪复活...
          </p>
        </div>
      </div>
    </div>
    
    <!-- 任务面板 -->
    <div v-if="showQuestPanel" class="quest-panel">
      <div class="panel-header">
        <h3>📜 {{ selectedLocation.name }}的任务</h3>
        <button class="close-btn" @click="showQuestPanel = false">×</button>
      </div>
      <div class="quest-list">
        <div v-if="availableQuests.length === 0" class="no-quest">
          暂无可用任务
        </div>
        <div v-for="quest in availableQuests" :key="quest.quest_id" class="quest-card">
          <h4>{{ quest.name }}</h4>
          <p>{{ quest.description }}</p>
          <div class="quest-rewards">
            <span class="reward exp">+{{ quest.exp_reward }} 经验</span>
            <span class="reward gold">+{{ quest.gold_reward }} 第纳尔</span>
          </div>
          <button class="accept-btn" @click="acceptQuest(quest)">接受任务</button>
        </div>
      </div>
    </div>
    
    <!-- 底部状态栏 -->
    <div class="map-footer">
      <div class="player-info">
        <span>位置: {{ currentLocationName }}</span>
        <span v-if="isTraveling">旅行中: {{ Math.round(playerState.travel_progress) }}%</span>
      </div>
      <div class="zoom-hint">
        <span>滚轮缩放</span>
        <span>点击地点查看详情</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { wsService } from '../services/websocket'

interface Location {
  location_id: string
  name: string
  location_type: number
  x: number
  y: number
  description: string
  faction: number
  faction_name: string
  prosperity?: number
  production?: string
  garrison_size?: number
  difficulty?: number
  rewards?: number
}

interface Bandit {
  bandit_id: string
  name: string
  type: string
  icon: string
  x: number
  y: number
  level: number
  member_count: number
  hp: number
  max_hp: number
  is_defeated: boolean
  defeated_time_remaining: number
}

interface Quest {
  quest_id: string
  name: string
  description: string
  difficulty: number
  exp_reward: number
  gold_reward: number
  duration: number
}

interface PlayerState {
  x: number
  y: number
  current_location: string
  travel_progress: number
  travel_destination: string
  travel_time: number
}

const props = defineProps<{
  locations: Location[]
  playerState: PlayerState
  bandits?: Bandit[]
}>()

const emit = defineEmits<{
  (e: 'select-location', location: Location): void
  (e: 'travel', locationId: string): void
  (e: 'get-quest', locationId: string): void
  (e: 'accept-quest', quest: Quest): void
  (e: 'battle', locationId: string): void
  (e: 'attack-bandit', banditId: string): void
}>()

const mapViewport = ref<HTMLElement | null>(null)
const selectedLocation = ref<Location | null>(null)
const selectedBandit = ref<Bandit | null>(null)
const showQuestPanel = ref(false)
const availableQuests = ref<Quest[]>([])
const scale = ref(1)

const isTraveling = computed(() => props.playerState.travel_destination !== '')

const currentLocationName = computed(() => {
  if (props.playerState.current_location) {
    const loc = props.locations.find(l => l.location_id === props.playerState.current_location)
    return loc?.name || '未知'
  }
  return '野外'
})

const travelIndicatorX = computed(() => {
  if (!isTraveling.value) return 0
  const dest = props.locations.find(l => l.location_id === props.playerState.travel_destination)
  if (!dest) return 0
  const progress = props.playerState.travel_progress / 100
  return props.playerState.x + (dest.x - props.playerState.x) * progress
})

const travelIndicatorY = computed(() => {
  if (!isTraveling.value) return 0
  const dest = props.locations.find(l => l.location_id === props.playerState.travel_destination)
  if (!dest) return 0
  const progress = props.playerState.travel_progress / 100
  return props.playerState.y + (dest.y - props.playerState.y) * progress
})

function handleMapClick(event: MouseEvent) {
  selectedLocation.value = null
}

function handleWheel(event: WheelEvent) {
  event.preventDefault()
  const delta = event.deltaY > 0 ? -0.1 : 0.1
  scale.value = Math.max(0.5, Math.min(2, scale.value + delta))
}

function selectLocation(location: Location) {
  selectedLocation.value = location
  emit('select-location', location)
}

function isNearby(location: Location): boolean {
  const dx = location.x - props.playerState.x
  const dy = location.y - props.playerState.y
  const distance = Math.sqrt(dx * dx + dy * dy)
  return distance < 80
}

function canTravelTo(location: Location): boolean {
  if (isTraveling.value) return false
  if (props.playerState.current_location === location.location_id) return false
  return true
}

function canGetQuest(location: Location): boolean {
  if (location.location_type === 3) return false // 匪窝不给任务
  return true
}

function canTrade(location: Location): boolean {
  return location.location_type === 1 // 只有城镇可以交易
}

function canBattle(location: Location): boolean {
  return location.location_type === 3 // 只有匪窝可以挑战
}

function getTravelTime(location: Location): number {
  const dx = location.x - props.playerState.x
  const dy = location.y - props.playerState.y
  const distance = Math.sqrt(dx * dx + dy * dy)
  return Math.round(distance / 10) // 简化计算
}

function travelTo(location: Location) {
  emit('travel', location.location_id)
  selectedLocation.value = null
}

function getQuest(location: Location) {
  showQuestPanel.value = true
  emit('get-quest', location.location_id)
  wsService.send('get_quests', { location_id: location.location_id })
}

function acceptQuest(quest: Quest) {
  emit('accept-quest', quest)
  showQuestPanel.value = false
}

function startBattle(location: Location) {
  emit('battle', location.location_id)
}

function selectBandit(bandit: Bandit) {
  selectedBandit.value = bandit
  selectedLocation.value = null // 取消选中地点
}

function attackBandit(bandit: Bandit) {
  if (bandit.is_defeated) return
  emit('attack-bandit', bandit.bandit_id)
  selectedBandit.value = null
}

function getBanditColor(level: number): string {
  if (level >= 8) return '#dc2626'  // 红色 - 精英
  if (level >= 5) return '#f97316'   // 橙色 - 高级
  if (level >= 3) return '#eab308'   // 黄色 - 中级
  return '#22c55e'                   // 绿色 - 初级
}

function getBanditTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    '山贼': '⚔️',
    '海寇': '☠️',
    '草原强盗': '🏇',
    '沙漠盗贼': '🐪',
    '森林盗匪': '🌲',
    '山地匪徒': '⛰️',
  }
  return icons[type] || '⚔️'
}

function getBanditDistance(bandit: Bandit): number {
  const dx = bandit.x - props.playerState.x
  const dy = bandit.y - props.playerState.y
  return Math.round(Math.sqrt(dx * dx + dy * dy))
}

function getLocationTypeName(type: number): string {
  const names = ['村庄', '城镇', '城堡', '匪窝']
  return names[type] || '未知'
}

function getLocationTypeClass(type: number): string {
  const classes = ['village', 'town', 'castle', 'bandit']
  return classes[type] || ''
}

function getFactionColor(faction: number): string {
  const colors = ['#8b5cf6', '#3b82f6', '#64748b', '#a855f7', '#f59e0b', '#ef4444']
  return colors[faction] || '#fff'
}

function handleQuestData(data: any) {
  if (data.quests) {
    availableQuests.value = data.quests
  }
}

onMounted(() => {
  wsService.on('quests_data', handleQuestData)
})
</script>

<style scoped>
.map-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0a0a12;
  color: #fff;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(20, 20, 30, 0.95);
  border-bottom: 1px solid #2a2a3e;
}

.map-header h2 {
  margin: 0;
  font-size: 18px;
}

.map-legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #888;
}

.legend-item .icon {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-item .icon.town { background: #4a9eff; }
.legend-item .icon.castle { background: #ef4444; }
.legend-item .icon.village { background: #22c55e; }
.legend-item .icon.bandit { background: #dc2626; }

.map-viewport {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.map-svg {
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

.location-icon {
  cursor: pointer;
  transition: transform 0.2s;
}

.location-icon:hover {
  transform: scale(1.2);
}

.location-icon.selected circle {
  stroke-width: 4;
  filter: url(#glow);
}

.location-icon.player-here circle {
  stroke: #fbbf24;
  stroke-width: 4;
}

.location-icon.nearby circle {
  stroke: #4ade80;
  stroke-width: 2;
}

.travel-line {
  animation: dash 1s linear infinite;
}

@keyframes dash {
  to { stroke-dashoffset: -10; }
}

.location-name {
  pointer-events: none;
  text-shadow: 0 1px 3px rgba(0,0,0,0.8);
}

.player-marker {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.location-panel, .quest-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  width: 320px;
  background: rgba(30, 30, 46, 0.98);
  border-radius: 12px;
  border: 1px solid #3a3a4e;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(0,0,0,0.3);
  border-bottom: 1px solid #2a2a3e;
}

.panel-header h3 {
  margin: 0;
  flex: 1;
}

.location-type-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
}

.location-type-badge.town { background: rgba(74,158,255,0.2); color: #4a9eff; }
.location-type-badge.castle { background: rgba(239,68,68,0.2); color: #ef4444; }
.location-type-badge.village { background: rgba(34,197,94,0.2); color: #22c55e; }
.location-type-badge.bandit { background: rgba(220,38,38,0.2); color: #dc2626; }

.close-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: #3a3a4e;
  color: #fff;
  cursor: pointer;
}

.panel-content {
  padding: 16px;
}

.location-desc {
  font-size: 13px;
  color: #aaa;
  line-height: 1.5;
  margin-bottom: 16px;
}

.location-stats {
  margin-bottom: 16px;
}

.stat {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #2a2a3e;
}

.stat .label {
  color: #888;
  font-size: 13px;
}

.stat .value {
  color: #fff;
  font-size: 13px;
}

.location-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.travel { background: #4a9eff; color: #fff; }
.action-btn.quest { background: #8b5cf6; color: #fff; }
.action-btn.trade { background: #22c55e; color: #fff; }
.action-btn.battle { background: #ef4444; color: #fff; }
.action-btn.current { background: #3a3a4e; color: #888; cursor: not-allowed; }

.action-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.quest-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 16px;
}

.no-quest {
  text-align: center;
  color: #888;
  padding: 20px;
}

.quest-card {
  background: rgba(0,0,0,0.3);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.quest-card h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
}

.quest-card p {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #aaa;
}

.quest-rewards {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.reward {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.reward.exp { background: rgba(139,92,246,0.2); color: #a78bfa; }
.reward.gold { background: rgba(245,158,11,0.2); color: #fbbf24; }

.accept-btn {
  width: 100%;
  padding: 8px;
  border: none;
  border-radius: 6px;
  background: #4a9eff;
  color: #fff;
  cursor: pointer;
}

.accept-btn:hover {
  background: #3b82f6;
}

.map-footer {
  display: flex;
  justify-content: space-between;
  padding: 12px 24px;
  background: rgba(20, 20, 30, 0.95);
  border-top: 1px solid #2a2a3e;
  font-size: 12px;
  color: #888;
}

.player-info {
  display: flex;
  gap: 24px;
}

.zoom-hint {
  display: flex;
  gap: 16px;
}

/* 劫匪样式 */
.bandit-marker-group {
  cursor: pointer;
}

.bandit-icon {
  cursor: pointer;
  transition: transform 0.2s;
}

.bandit-icon:hover {
  transform: scale(1.2);
}

.bandit-icon.selected circle {
  stroke-width: 3;
  filter: url(#glow);
}

.bandit-icon.defeated {
  opacity: 0.5;
  cursor: default;
}

.bandit-icon.low-hp circle {
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.bandit-panel .panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bandit-status {
  text-align: center;
  padding: 20px;
  background: rgba(0,0,0,0.3);
  border-radius: 8px;
  margin-bottom: 16px;
}

.defeated-text {
  font-size: 18px;
  color: #dc2626;
  margin-bottom: 8px;
}

.respawn-text {
  font-size: 14px;
  color: #888;
}

.bandit-stats {
  margin-bottom: 16px;
}

.level-1 { color: #22c55e; }
.level-2 { color: #eab308; }
.level-3 { color: #f97316; }
.level-4 { color: #dc2626; }

.hp-bar-container {
  margin-bottom: 16px;
}

.hp-bar {
  height: 8px;
  background: #333;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 4px;
}

.hp-fill {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #dc2626);
  transition: width 0.3s;
}

.hp-text {
  font-size: 12px;
  color: #888;
}

.bandit-rewards {
  margin-bottom: 16px;
}

.bandit-rewards h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #888;
}

.reward-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #2a2a3e;
}

.reward-icon {
  font-size: 16px;
}

.reward-label {
  flex: 1;
  color: #888;
  font-size: 13px;
}

.reward-value {
  color: #fbbf24;
  font-size: 14px;
  font-weight: bold;
}

.action-btn.attack {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  color: #fff;
}

.action-btn.attack:hover {
  background: linear-gradient(135deg, #ef4444, #dc2626);
}

.waiting-text {
  text-align: center;
  color: #888;
  font-size: 14px;
  padding: 12px;
}
</style>
