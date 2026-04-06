<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/home')">← 返回</el-button>
      <h2>🌿 采集</h2>
      <div class="player-stats">
        <span>体力: {{ player?.lingqi ?? 0 }}/{{ player?.max_lingqi ?? 50 }}</span>
        <span>草药学: Lv.{{ herbalismLevel }}</span>
        <span v-if="cooldownRemaining" class="cooldown">冷却: {{ cooldownRemaining }}s</span>
        <span v-else class="ready">就绪</span>
      </div>
    </div>

    <div class="gathering-content">
      <div class="herb-list">
        <div v-for="herb in herbList" :key="herb.id" class="herb-card">
          <div class="herb-info">
            <div class="herb-icon">{{ herb.icon }}</div>
            <div class="herb-details">
              <h3>{{ herb.name }} <span class="rarity-badge" :class="rarityClass(herb.rarity)">{{ herb.rarityLabel }}</span></h3>
              <p>{{ herb.description }}</p>
              <div class="herb-stats">
                <span>药效: {{ herb.heal }} HP</span>
                <span>采集率: {{ herb.rate }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="gather-action">
        <button
          class="gather-btn"
          :disabled="!canGather || isGathering"
          @click="gather"
        >
          {{ isGathering ? '采集中...' : canGather ? '🌿 开始采集' : '无法采集' }}
        </button>
        <p class="gather-hint">随机采集草药，草药学等级影响产出</p>
      </div>

      <div class="gathering-stats">
        <h4>📊 采集统计</h4>
        <div class="stat-row">
          <span>今日采集</span>
          <span>{{ gatherCount }} 次</span>
        </div>
        <div class="stat-row">
          <span>消耗体力</span>
          <span>{{ gatherCount * 10 }} 点</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useLogStore } from '../stores/log'
import { ElMessage } from 'element-plus'

const router = useRouter()
const gameStore = useGameStore()
const logStore = useLogStore()

const isGathering = ref(false)
const gatherCount = ref(0)
const cooldownRemaining = ref(0)
let cooldownTimer = null

const player = computed(() => gameStore.player)
const herbalismLevel = computed(() => player.value?.skills?.[31] ?? 0)
const canGather = computed(() => {
  if (!player.value) return false
  return (player.value.lingqi ?? 0) >= 10 && cooldownRemaining.value <= 0
})

const herbList = [
  { id: 'herb_common', name: '普通草药', icon: '🌱', rarity: 0.6, rarityLabel: '常见', heal: 20, rate: 60, description: '野外常见的草药，可用于制作绷带' },
  { id: 'herb_good', name: '优质草药', icon: '🌿', rarity: 0.3, rarityLabel: '稀有', heal: 40, rate: 30, description: '药效较好的草药' },
  { id: 'herb_rare', name: '珍稀草药', icon: '🍄', rarity: 0.1, rarityLabel: '珍稀', heal: 80, rate: 10, description: '很难采集到的珍稀草药' },
  { id: 'herb_lingzhi', name: '灵芝', icon: '✨', rarity: 0.02, rarityLabel: '极珍稀', heal: 120, rate: 2, description: '珍贵的灵芝，有奇效' },
  { id: 'herb_ginseng', name: '千年人参', icon: '👑', rarity: 0.01, rarityLabel: '传说', heal: 200, rate: 1, description: '传说中的千年人参，药效极强' },
]

const rarityClass = (r) => {
  if (r >= 0.5) return 'r-common'
  if (r >= 0.2) return 'r-uncommon'
  if (r >= 0.05) return 'r-rare'
  if (r >= 0.015) return 'r-epic'
  return 'r-legendary'
}

const gather = () => {
  if (!canGather.value || isGathering.value) return
  isGathering.value = true
  gameStore.send({ type: 'gather_herbs' })
}

const handleWsMessage = (msg) => {
  if (msg.type === 'action_result' && msg.action === 'gather_herbs') {
    isGathering.value = false
    if (msg.data?.success) {
      ElMessage.success(msg.data.message)
      gatherCount.value++
      cooldownRemaining.value = 5
      startCooldownTimer()
      logStore.addLog({ type: 'gather', icon: '🌿', title: '采集成功', content: msg.data.message })
      gameStore.getPanel()
    } else {
      ElMessage.error(msg.data?.message || '采集失败')
    }
  }
}

const startCooldownTimer = () => {
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    cooldownRemaining.value = Math.max(0, cooldownRemaining.value - 1)
    if (cooldownRemaining.value <= 0) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

onMounted(async () => {
  if (!gameStore.token) { router.push('/'); return }
  if (!gameStore.connected) await gameStore.connectWs()
  gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
  gameStore.wsMessageHandlers['gathering'] = handleWsMessage
  gameStore.getPanel()
  logStore.init()
})

onUnmounted(() => {
  if (gameStore.wsMessageHandlers?.gathering) delete gameStore.wsMessageHandlers.gathering
  if (cooldownTimer) clearInterval(cooldownTimer)
})
</script>

<style scoped>
.view-container {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: rgba(20,20,30,0.95);
  border-bottom: 1px solid #2a2a3e;
}

.back-btn {
  background: rgba(255,255,255,0.08) !important;
  border: 1px solid rgba(255,255,255,0.15) !important;
  color: #ccc !important;
}

.page-header h2 {
  color: var(--text-gold);
  margin: 0;
  font-size: 20px;
}

.player-stats {
  margin-left: auto;
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #aaa;
}

.cooldown { color: #f97316; }
.ready { color: #22c55e; }

.gathering-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.herb-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 24px;
}

.herb-card {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  background: rgba(25,25,40,0.95);
  border: 1px solid #2a2a3e;
  border-radius: 10px;
}

.herb-info {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
}

.herb-icon {
  font-size: 36px;
  flex-shrink: 0;
}

.herb-details {
  flex: 1;
}

.herb-details h3 {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.rarity-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.r-common { background: rgba(158,158,158,0.2); color: #9e9e9e; }
.r-uncommon { background: rgba(76,175,80,0.2); color: #4caf50; }
.r-rare { background: rgba(33,150,243,0.2); color: #2196f3; }
.r-epic { background: rgba(156,39,176,0.2); color: #9c27b0; }
.r-legendary { background: rgba(255,152,0,0.2); color: #ff9800; }

.herb-details p {
  margin: 0 0 6px 0;
  font-size: 12px;
  color: #888;
}

.herb-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #aaa;
}

.gather-action {
  text-align: center;
  margin-bottom: 24px;
}

.gather-btn {
  padding: 14px 40px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.gather-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(34,197,94,0.4);
}

.gather-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.gather-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.gathering-stats {
  background: rgba(0,0,0,0.3);
  border: 1px solid #2d2d2d;
  border-radius: 8px;
  padding: 16px;
}

.gathering-stats h4 {
  margin: 0 0 12px 0;
  color: var(--text-gold);
  font-size: 14px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
  color: #aaa;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.stat-row:last-child { border-bottom: none; }
.stat-row span:last-child { color: #fff; }
</style>
