<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/home')">← 返回</el-button>
      <h2>🏹 狩猎</h2>
      <div class="player-stats">
        <span>体力: {{ player?.lingqi ?? 0 }}/{{ player?.max_lingqi ?? 50 }}</span>
        <span v-if="cooldownRemaining" class="cooldown">冷却: {{ formatCooldown(cooldownRemaining) }}</span>
        <span v-else class="ready">就绪</span>
      </div>
    </div>

    <div class="hunting-content">
      <div class="wildlife-list">
        <div
          v-for="w in wildlifeList"
          :key="w.id"
          class="wildlife-card"
          :class="{ 'can-hunt': canHunt && !isHunting }"
        >
          <div class="wildlife-info">
            <div class="wildlife-icon">{{ w.icon }}</div>
            <div class="wildlife-details">
              <h3>{{ w.name }} <span class="tier-badge" :class="tierClass(w.tier)">{{ tierName(w.tier) }}</span></h3>
              <p class="wildlife-desc">{{ w.description }}</p>
              <div class="wildlife-drops">
                <span class="drop-label">掉落:</span>
                <span v-for="(chance, itemId) in w.drops" :key="itemId" class="drop-item">
                  {{ dropName(itemId) }} ({{ Math.round(chance * 100) }}%)
                </span>
              </div>
              <div class="wildlife-rewards">
                <span class="reward exp">✨ +{{ w.exp }} 经验</span>
                <span class="reward gold">💰 +{{ w.gold }} 第纳尔</span>
              </div>
            </div>
          </div>
          <button
            class="hunt-btn"
            :disabled="!canHunt || isHunting"
            @click="hunt(w.id)"
          >
            {{ isHunting ? '狩猎中...' : canHunt ? '🏹 狩猎' : '冷却中' }}
          </button>
        </div>
      </div>

      <div class="hunting-stats">
        <h4>📊 狩猎统计</h4>
        <div class="stat-row">
          <span>今日狩猎</span>
          <span>{{ huntCount }} 次</span>
        </div>
        <div class="stat-row">
          <span>消耗体力</span>
          <span>{{ huntCount * 15 }} 点</span>
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

const isHunting = ref(false)
const huntCount = ref(0)
const cooldownRemaining = ref(0)
let cooldownTimer = null

const player = computed(() => gameStore.player)
const canHunt = computed(() => {
  if (!player.value) return false
  return (player.value.lingqi ?? 0) >= 15 && cooldownRemaining.value <= 0
})

const wildlifeList = [
  { id: 'deer', name: '鹿', icon: '🦌', tier: 0, description: '森林中常见的温顺动物', exp: 15, gold: 10, drops: { hunt_deer_skin: 0.8, hunt_deer_meat: 0.9, hunt_deer_antler: 0.3 } },
  { id: 'rabbit', name: '野兔', icon: '🐇', tier: 0, description: '草地常见的小动物', exp: 8, gold: 5, drops: { hunt_rabbit_skin: 0.7, hunt_rabbit_meat: 0.9 } },
  { id: 'chicken', name: '野鸡', icon: '🐔', tier: 0, description: '村庄附近的野生禽类', exp: 5, gold: 3, drops: { hunt_feather: 0.8, hunt_chicken_meat: 0.9 } },
  { id: 'boar', name: '野猪', icon: '🐗', tier: 1, description: '具有攻击性的野兽', exp: 30, gold: 25, drops: { hunt_boar_skin: 0.8, hunt_boar_meat: 0.9, hunt_boar_tusk: 0.4 } },
  { id: 'wolf', name: '狼', icon: '🐺', tier: 1, description: '成群出现的捕食者', exp: 35, gold: 30, drops: { hunt_wolf_skin: 0.8, hunt_wolf_fang: 0.5 } },
  { id: 'bear', name: '熊', icon: '🐻', tier: 2, description: '凶猛的大型野兽', exp: 80, gold: 60, drops: { hunt_bear_skin: 0.7, hunt_bear_paw: 0.4, hunt_bear_gall: 0.2 } },
  { id: 'mammoth', name: '猛犸象', icon: '🦣', tier: 3, description: '传说中的远古巨兽', exp: 200, gold: 150, drops: { hunt_mammoth_tusk: 0.3, hunt_mammoth_hide: 0.5 } },
]

const tierClass = (t) => ['', 'tier-common', 'tier-advanced', 'tier-rare', 'tier-boss'][t] || ''
const tierName = (t) => ['普通', '进阶', '高级', 'Boss'][t] || '未知'
const dropName = (id) => id.replace('hunt_', '').replace(/_/g, ' ')
const formatCooldown = (s) => {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}

const hunt = async (wildlifeId) => {
  if (!canHunt.value || isHunting.value) return
  
  const requiredLingqi = 15
  const currentLingqi = player.value?.lingqi ?? 0
  
  if (currentLingqi < requiredLingqi) {
    ElMessage.error(`体力不足，需要 ${requiredLingqi} 点体力`)
    return
  }
  
  isHunting.value = true
  gameStore.send({ type: 'hunt_wildlife', data: { wildlife_id: wildlifeId } })
}

const handleWsMessage = (msg) => {
  if (msg.type === 'action_result' && msg.action === 'hunt_wildlife') {
    isHunting.value = false
    if (msg.data?.success) {
      ElMessage.success(msg.data.message)
      huntCount.value++
      cooldownRemaining.value = 300
      startCooldownTimer()
      logStore.addLog({ type: 'gather', icon: '🏹', title: `狩猎 ${msg.data.message?.split('！')[0] || '成功'}`, content: msg.data.message })
      gameStore.getPanel()
    } else {
      ElMessage.error(msg.data?.message || '狩猎失败')
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
  gameStore.wsMessageHandlers['hunting'] = handleWsMessage
  gameStore.getPanel()
  logStore.init()
})

onUnmounted(() => {
  if (gameStore.wsMessageHandlers?.hunting) delete gameStore.wsMessageHandlers.hunting
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

.hunting-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.wildlife-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.wildlife-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: rgba(25,25,40,0.95);
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  transition: all 0.2s;
}

.wildlife-card.can-hunt:hover {
  border-color: rgba(212,175,55,0.3);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.wildlife-icon {
  font-size: 40px;
  flex-shrink: 0;
}

.wildlife-details {
  flex: 1;
}

.wildlife-details h3 {
  margin: 0 0 4px 0;
  font-size: 15px;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tier-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.tier-common { background: rgba(158,158,158,0.2); color: #9e9e9e; }
.tier-advanced { background: rgba(76,175,80,0.2); color: #4caf50; }
.tier-rare { background: rgba(249,115,22,0.2); color: #f97316; }
.tier-boss { background: rgba(220,38,38,0.2); color: #dc2626; }

.wildlife-desc {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #888;
}

.wildlife-drops {
  font-size: 11px;
  color: #aaa;
  margin-bottom: 6px;
}

.drop-label { color: #888; margin-right: 4px; }
.drop-item { margin-right: 8px; }

.wildlife-rewards {
  display: flex;
  gap: 12px;
}

.reward {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}

.reward.exp { background: rgba(139,92,246,0.2); color: #a78bfa; }
.reward.gold { background: rgba(245,158,11,0.2); color: #fbbf24; }

.hunt-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.hunt-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(220,38,38,0.4);
}

.hunt-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.hunting-stats {
  background: rgba(0,0,0,0.3);
  border: 1px solid #2d2d2d;
  border-radius: 8px;
  padding: 16px;
}

.hunting-stats h4 {
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
