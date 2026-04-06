<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/home')">← 返回</el-button>
      <h2>🛡️ 部队</h2>
      <div class="player-stats">
        <span>💰 {{ player?.spirit_stones ?? 0 }} 第纳尔</span>
        <span>👥 {{ totalTroops }}/{{ maxTroops }}</span>
        <span>💸 军饷: {{ totalWage }}/日</span>
      </div>
    </div>

    <div class="troops-content">
      <div class="section-title">我的部队</div>
      <div v-if="myTroops.length === 0" class="empty-msg">
        还没有任何部队，去各地招募吧！
      </div>
      <div v-else class="troops-grid">
        <div v-for="t in myTroops" :key="t.troop_id" class="troop-card">
          <div class="troop-header">
            <div class="troop-icon">{{ factionIcon(t.faction) }}</div>
            <div class="troop-info">
              <h3>{{ t.name }}</h3>
              <span class="faction-tag" :class="factionClass(t.faction)">{{ t.faction_name }}</span>
            </div>
            <div class="troop-count">×{{ t.count }}</div>
          </div>
          <div class="troop-stats">
            <div class="stat"><span>⚔️攻击</span><span>{{ t.attack * t.count }}</span></div>
            <div class="stat"><span>🛡️防御</span><span>{{ t.defense * t.count }}</span></div>
            <div class="stat"><span>❤️生命</span><span>{{ t.hp * t.count }}</span></div>
            <div class="stat"><span>💸军饷</span><span>{{ t.total_wage }}/日</span></div>
          </div>
          <div class="dismiss-section">
            <el-input-number v-model="dismissCounts[t.troop_id]" :min="1" :max="t.count" size="small" />
            <el-button size="small" type="danger" @click="dismiss(t.troop_id)">解散</el-button>
          </div>
        </div>
      </div>

      <div class="section-title">可招募兵种</div>
      <div class="faction-tabs">
        <button
          v-for="f in factions"
          :key="f.id"
          class="faction-tab"
          :class="{ active: selectedFaction === f.id }"
          @click="selectedFaction = f.id"
        >
          {{ factionIcon(f.id) }} {{ f.name }}
        </button>
      </div>
      <div class="recruit-grid">
        <div v-for="t in filteredTroops" :key="t.troop_id" class="troop-card recruit">
          <div class="troop-header">
            <div class="troop-icon">{{ factionIcon(t.faction) }}</div>
            <div class="troop-info">
              <h3>{{ t.name }}</h3>
              <span class="faction-tag" :class="factionClass(t.faction)">{{ t.faction_name }}</span>
            </div>
          </div>
          <p class="troop-desc">{{ t.description }}</p>
          <div class="troop-stats">
            <div class="stat"><span>⚔️攻击</span><span>{{ t.attack }}</span></div>
            <div class="stat"><span>🛡️防御</span><span>{{ t.defense }}</span></div>
            <div class="stat"><span>❤️生命</span><span>{{ t.hp }}</span></div>
            <div class="stat"><span>💸军饷</span><span>{{ t.wage }}/日</span></div>
          </div>
          <div class="recruit-section">
            <span class="cost">💰 {{ t.cost }} 第纳尔/人</span>
            <el-input-number v-model="recruitCounts[t.troop_id]" :min="1" :max="100" size="small" />
            <button class="recruit-btn" @click="recruit(t.troop_id)">招募</button>
          </div>
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
const troopsData = ref({})
const selectedFaction = ref('swadia')
const recruitCounts = ref({})
const dismissCounts = ref({})

const factions = [
  { id: 'swadia', name: '斯瓦迪亚' },
  { id: 'vaegir', name: '维吉亚' },
  { id: 'nord', name: '诺德' },
  { id: 'rhodok', name: '罗多克' },
  { id: 'khergit', name: '库吉特' },
  { id: 'sarranid', name: '萨兰德' },
]

const myTroops = computed(() => troopsData.value.troops || [])
const totalTroops = computed(() => troopsData.value.total_count || 0)
const maxTroops = computed(() => troopsData.value.max_troops || 5)
const totalWage = computed(() => troopsData.value.total_wage || 0)
const allTroops = computed(() => troopsData.value.all_troops || [])
const filteredTroops = computed(() => allTroops.value.filter(t => t.faction === selectedFaction.value))

const factionIcon = (f) => {
  const map = { swadia: '🦁', vaegir: '🐺', nord: '🪓', rhodok: '🏰', khergit: '🏇', sarranid: '🐪' }
  return map[f] || '⚔️'
}

const factionClass = (f) => `faction-${f}`

const loadTroops = async () => {
  try {
    const resp = await fetch('/api/troops')
    const data = await resp.json()
    if (data.success) {
      troopsData.value = data
      data.troops?.forEach(t => { dismissCounts.value[t.troop_id] = 1 })
      data.all_troops?.forEach(t => { recruitCounts.value[t.troop_id] = 1 })
    }
  } catch (e) {
    console.error('加载部队失败', e)
  }
}

const recruit = async (troopId) => {
  const count = recruitCounts.value[troopId] || 1
  try {
    const resp = await fetch('/api/troops/recruit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ troop_id: troopId, count }),
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success(data.message)
      await loadTroops()
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

const dismiss = async (troopId) => {
  const count = dismissCounts.value[troopId] || 1
  try {
    const resp = await fetch('/api/troops/dismiss', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ troop_id: troopId, count }),
    })
    const data = await resp.json()
    if (data.success) {
      ElMessage.success(data.message)
      await loadTroops()
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

onMounted(() => {
  loadTroops()
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
  gap: 16px;
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

.faction-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.faction-tab {
  padding: 8px 16px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.faction-tab:hover {
  border-color: #d4a464;
  color: #e8e0d0;
}

.faction-tab.active {
  background: rgba(212, 164, 100, 0.2);
  border-color: #d4a464;
  color: #d4a464;
}

.troops-grid, .recruit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.troop-card {
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s;
}

.troop-card:hover {
  border-color: #d4a464;
}

.troop-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.troop-icon {
  font-size: 32px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(212, 164, 100, 0.1);
  border-radius: 50%;
}

.troop-info h3 {
  margin: 0;
  color: #e8e0d0;
  font-size: 15px;
}

.faction-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  color: #aaa;
}

.faction-swadia { background: rgba(100, 149, 237, 0.2); color: #6495ed; }
.faction-vaegir { background: rgba(135, 206, 250, 0.2); color: #87cefa; }
.faction-nord { background: rgba(176, 196, 222, 0.2); color: #b0c4de; }
.faction-rhodok { background: rgba(34, 139, 34, 0.2); color: #228b22; }
.faction-khergit { background: rgba(255, 165, 0, 0.2); color: #ffa500; }
.faction-sarranid { background: rgba(255, 215, 0, 0.2); color: #ffd700; }

.troop-count {
  margin-left: auto;
  font-size: 20px;
  font-weight: bold;
  color: #d4a464;
}

.troop-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin: 8px 0;
}

.stat {
  display: flex;
  gap: 4px;
  font-size: 12px;
  color: #888;
}

.stat span:last-child {
  color: #e8e0d0;
  font-weight: bold;
}

.troop-desc {
  color: #888;
  font-size: 12px;
  margin: 4px 0;
}

.recruit-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.cost {
  color: #d4a464;
  font-weight: bold;
  font-size: 13px;
}

.recruit-btn {
  padding: 6px 16px;
  background: linear-gradient(135deg, #d4a464, #b8860b);
  border: none;
  border-radius: 4px;
  color: #1a1a2e;
  font-weight: bold;
  cursor: pointer;
  font-size: 13px;
  transition: opacity 0.2s;
}

.recruit-btn:hover {
  opacity: 0.85;
}

.dismiss-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
</style>
