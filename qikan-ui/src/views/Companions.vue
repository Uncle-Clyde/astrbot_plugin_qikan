<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/home')">← 返回</el-button>
      <h2>🤝 同伴</h2>
      <div class="player-stats">
        <span>💰 {{ player?.spirit_stones ?? 0 }} 第纳尔</span>
      </div>
    </div>

    <div class="companions-content">
      <div class="section-title">已招募同伴</div>
      <div v-if="ownedCompanions.length === 0" class="empty-msg">
        尚未招募任何同伴，去酒馆看看吧！
      </div>
      <div v-else class="owned-grid">
        <div v-for="c in ownedCompanions" :key="c.companion_id" class="companion-card owned">
          <div class="companion-header">
            <div class="companion-avatar">{{ getAvatar(c.title) }}</div>
            <div class="companion-name">
              <h3>{{ c.name }}</h3>
              <span class="title-badge">{{ c.title }}</span>
            </div>
            <el-switch
              v-model="c.is_active"
              active-text="出战"
              inactive-text="休息"
              @change="toggleActive(c)"
            />
          </div>
          <div class="companion-stats">
            <div class="stat"><span>⚔️攻击</span><span>{{ c.attack }}</span></div>
            <div class="stat"><span>🛡️防御</span><span>{{ c.defense }}</span></div>
            <div class="stat"><span>❤️生命</span><span>{{ c.hp }}</span></div>
          </div>
          <div class="loyalty-bar">
            <div class="loyalty-label">
              <span>忠诚度</span>
              <span>{{ c.loyalty }}%</span>
            </div>
            <div class="loyalty-track">
              <div class="loyalty-fill" :style="{ width: c.loyalty + '%' }" :class="loyaltyClass(c.loyalty)"></div>
            </div>
          </div>
          <div class="buff-info" v-if="c.buff && c.is_active">
            <span class="buff-label">出战加成:</span>
            <span v-if="c.buff.attack > 0">⚔️+{{ c.buff.attack }}</span>
            <span v-if="c.buff.defense > 0">🛡️+{{ c.buff.defense }}</span>
            <span v-if="c.buff.hp > 0">❤️+{{ c.buff.hp }}</span>
            <span v-if="c.buff.crit > 0">💥+{{ c.buff.crit }}%</span>
          </div>
          <div class="gift-section">
            <span class="gift-label">赠送礼物:</span>
            <el-select v-model="giftSelections[c.companion_id]" size="small" placeholder="选择礼物">
              <el-option
                v-for="(g, gid) in gifts"
                :key="gid"
                :label="g.description + ` (${g.base_price}💰)`"
                :value="gid"
              />
            </el-select>
            <el-button size="small" type="primary" @click="giveGift(c.companion_id)">赠送</el-button>
          </div>
        </div>
      </div>

      <div class="section-title">可招募同伴</div>
      <div class="recruit-grid">
        <div v-for="c in availableCompanions" :key="c.companion_id" class="companion-card recruit">
          <div class="companion-header">
            <div class="companion-avatar">{{ getAvatar(c.title) }}</div>
            <div class="companion-name">
              <h3>{{ c.name }}</h3>
              <span class="title-badge">{{ c.title }}</span>
            </div>
          </div>
          <p class="companion-desc">{{ c.description }}</p>
          <div class="companion-stats">
            <div class="stat"><span>⚔️攻击</span><span>{{ c.attack }}</span></div>
            <div class="stat"><span>🛡️防御</span><span>{{ c.defense }}</span></div>
            <div class="stat"><span>❤️生命</span><span>{{ c.hp }}</span></div>
          </div>
          <div class="buff-preview">
            <span>招募加成: </span>
            <span v-if="c.buff_type === 'attack'">⚔️攻击+{{ c.buff_value }}</span>
            <span v-if="c.buff_type === 'defense'">🛡️防御+{{ c.buff_value }}</span>
            <span v-if="c.buff_type === 'hp'">❤️生命+{{ c.buff_value }}</span>
            <span v-if="c.buff_type === 'crit'">💥暴击+{{ c.buff_value }}%</span>
            <span v-if="c.buff_type === 'all'">全属性+{{ c.buff_value }}</span>
          </div>
          <div class="recruit-info">
            <span class="location">📍 {{ c.recruit_location }}</span>
            <span class="cost">💰 {{ c.recruit_cost }} 第纳尔</span>
          </div>
          <button class="recruit-btn" @click="recruit(c.companion_id)">招募</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'

const gameStore = useGameStore()
const player = computed(() => gameStore.player)
const companions = ref([])
const gifts = ref({})
const giftSelections = ref({})

const ownedCompanions = computed(() => companions.value.filter(c => c.is_owned))
const availableCompanions = computed(() => companions.value.filter(c => !c.is_owned))

const getAvatar = (title) => {
  const map = { '草原斥候': '🏇', '诺德女战士': '🪓', '战场医师': '💊', '罗多克神射手': '🏹', '维吉亚猎人': '🌲', '前海盗头目': '🏴‍☠️', '流浪学者': '📚', '沙漠佣兵': '🏜️', '驯马师': '🐴', '萨兰德舞者': '💃', '斯瓦迪亚骑士': '⚔️', '纪律教官': '📋' }
  return map[title] || '👤'
}

const loyaltyClass = (loyalty) => {
  if (loyalty >= 80) return 'loyalty-high'
  if (loyalty >= 50) return 'loyalty-mid'
  return 'loyalty-low'
}

const loadCompanions = async () => {
  try {
    const resp = await fetch('/api/companions')
    const data = await resp.json()
    if (data.success) {
      companions.value = data.companions
      gifts.value = data.gifts || {}
      companions.value.forEach(c => {
        giftSelections.value[c.companion_id] = ''
      })
    }
  } catch (e) {
    console.error('加载同伴失败', e)
  }
}

const recruit = async (companionId) => {
  try {
    const resp = await fetch('/api/companions/recruit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ companion_id: companionId }),
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success(data.message)
      await loadCompanions()
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

const giveGift = async (companionId) => {
  const giftId = giftSelections.value[companionId]
  if (!giftId) {
    ElMessage.warning('请先选择礼物')
    return
  }
  try {
    const resp = await fetch('/api/companions/gift', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ companion_id: companionId, gift_id: giftId }),
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success(data.message)
      await loadCompanions()
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

const toggleActive = async (companion) => {
  try {
    const resp = await fetch('/api/companions/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ companion_id: companion.companion_id, active: companion.is_active }),
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success(data.message)
    } else {
      ElMessage.error(data.message)
      companion.is_active = !companion.is_active
    }
  } catch (e) {
    ElMessage.error('请求失败')
    companion.is_active = !companion.is_active
  }
}

onMounted(() => {
  loadCompanions()
})
</script>

<style scoped>
.view-container {
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  flex: 1;
  color: #d4a464;
}

.player-stats {
  display: flex;
  gap: 12px;
  color: #aaa;
  font-size: 14px;
}

.section-title {
  font-size: 18px;
  color: #d4a464;
  margin: 20px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #2a2a3e;
}

.empty-msg {
  text-align: center;
  color: #666;
  padding: 40px;
  font-size: 16px;
}

.owned-grid, .recruit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.companion-card {
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s;
}

.companion-card:hover {
  border-color: #d4a464;
}

.companion-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.companion-avatar {
  font-size: 36px;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(212, 164, 100, 0.1);
  border-radius: 50%;
}

.companion-name h3 {
  margin: 0;
  color: #e8e0d0;
  font-size: 16px;
}

.title-badge {
  font-size: 12px;
  color: #d4a464;
  background: rgba(212, 164, 100, 0.15);
  padding: 2px 8px;
  border-radius: 4px;
}

.companion-stats {
  display: flex;
  gap: 16px;
  margin: 8px 0;
}

.stat {
  display: flex;
  gap: 4px;
  font-size: 13px;
  color: #aaa;
}

.stat span:last-child {
  color: #e8e0d0;
  font-weight: bold;
}

.loyalty-bar {
  margin: 8px 0;
}

.loyalty-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
}

.loyalty-track {
  height: 6px;
  background: #1a1a2e;
  border-radius: 3px;
  overflow: hidden;
}

.loyalty-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}

.loyalty-high { background: #4caf50; }
.loyalty-mid { background: #ff9800; }
.loyalty-low { background: #f44336; }

.buff-info {
  margin: 8px 0;
  font-size: 13px;
  color: #4caf50;
  background: rgba(76, 175, 80, 0.1);
  padding: 6px 10px;
  border-radius: 4px;
}

.buff-label {
  font-weight: bold;
  margin-right: 6px;
}

.gift-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.gift-label {
  font-size: 13px;
  color: #888;
}

.companion-desc {
  color: #888;
  font-size: 13px;
  margin: 8px 0;
}

.buff-preview {
  margin: 8px 0;
  font-size: 13px;
  color: #4caf50;
}

.recruit-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin: 8px 0;
}

.location { color: #888; }
.cost { color: #d4a464; font-weight: bold; }

.recruit-btn {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #d4a464, #b8860b);
  border: none;
  border-radius: 6px;
  color: #1a1a2e;
  font-weight: bold;
  cursor: pointer;
  transition: opacity 0.2s;
  margin-top: 8px;
}

.recruit-btn:hover {
  opacity: 0.85;
}
</style>
