<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/home')">← 返回</el-button>
      <h2>🏟️ 竞技场</h2>
      <div class="player-stats">
        <span>💰 {{ player?.spirit_stones ?? 0 }} 第纳尔</span>
        <span>🏆 报名费: {{ entryFee }} 第纳尔</span>
      </div>
    </div>

    <div class="tournament-content">
      <div class="section-title">选择对手</div>
      <div class="opponents-grid">
        <div v-for="opp in opponents" :key="opp.opponent_id" class="opponent-card" :class="levelClass(opp.level)">
          <div class="opponent-header">
            <div class="opponent-avatar">{{ opponentAvatar(opp.level) }}</div>
            <div class="opponent-info">
              <h3>{{ opp.title }} {{ opp.name }}</h3>
              <span class="level-badge" :class="levelClass(opp.level)">难度 {{ opp.level }}</span>
            </div>
          </div>
          <div class="opponent-stats">
            <div class="stat"><span>⚔️攻击</span><span>{{ opp.attack }}</span></div>
            <div class="stat"><span>🛡️防御</span><span>{{ opp.defense }}</span></div>
            <div class="stat"><span>❤️生命</span><span>{{ opp.hp }}</span></div>
          </div>
          <div class="opponent-rewards">
            <span class="reward">🏆 奖金: {{ opp.reward_gold }} 第纳尔</span>
            <span class="reward">⭐ 声望: {{ opp.reward_dao_yun }}</span>
          </div>
          <button class="fight-btn" :disabled="isFighting" @click="startBattle(opp)">
            {{ isFighting ? '战斗中...' : '⚔️ 挑战' }}
          </button>
        </div>
      </div>

      <div v-if="currentBattle" class="battle-section">
        <div class="section-title">当前战斗</div>
        <div class="battle-arena">
          <div class="fighter player-side">
            <div class="fighter-name">你</div>
            <div class="hp-bar">
              <div class="hp-fill hp-player" :style="{ width: playerHpPercent + '%' }"></div>
              <span class="hp-text">{{ battleState.player_hp }}/{{ battleState.player_max_hp }}</span>
            </div>
          </div>
          <div class="vs">VS</div>
          <div class="fighter enemy-side">
            <div class="fighter-name">{{ currentBattle.opponent.title }} {{ currentBattle.opponent.name }}</div>
            <div class="hp-bar">
              <div class="hp-fill hp-enemy" :style="{ width: enemyHpPercent + '%' }"></div>
              <span class="hp-text">{{ battleState.enemy_hp }}/{{ battleState.enemy_max_hp }}</span>
            </div>
          </div>
        </div>
        <div class="combat-log">
          <div v-for="(log, i) in battleState.combat_log" :key="i" class="log-entry">{{ log }}</div>
        </div>
        <div class="battle-actions">
          <button class="action-btn" @click="doAction('attack')">⚔️ 攻击</button>
          <button class="action-btn" @click="doAction('defend')">🛡️ 防御</button>
          <button class="action-btn" @click="doAction('charge')">🐎 冲锋</button>
          <button class="action-btn" @click="doAction('shield_bash')">💥 盾击</button>
          <button class="action-btn" @click="doAction('berserk')">🔥 狂暴</button>
        </div>
      </div>

      <div class="section-title">连胜奖励</div>
      <div class="streak-rewards">
        <div v-for="(reward, count) in streakRewards" :key="count" class="streak-card">
          <div class="streak-count">{{ count }}连胜</div>
          <div class="strew-title">{{ reward.title }}</div>
          <div class="streak-bonus">💰+{{ reward.gold }} ⭐+{{ reward.dao_yun }}</div>
        </div>
      </div>

      <div class="section-title">战斗记录</div>
      <div v-if="history.length === 0" class="empty-msg">暂无战斗记录</div>
      <div v-else class="history-list">
        <div v-for="(h, i) in history" :key="i" class="history-item" :class="h.result">
          <span class="result-icon">{{ h.result === 'win' ? '✅' : '❌' }}</span>
          <span class="opponent-name">{{ h.opponent_id }}</span>
          <span class="reward-text" v-if="h.result === 'win'">+{{ h.reward_gold }}💰 +{{ h.reward_dao_yun }}⭐</span>
          <span class="streak-text" v-if="h.win_streak > 1">🔥{{ h.win_streak }}连胜</span>
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
const opponents = ref([])
const entryFee = ref(30)
const streakRewards = ref({})
const history = ref([])
const isFighting = ref(false)
const currentBattle = ref(null)
const battleState = ref({
  player_hp: 0, player_max_hp: 100, enemy_hp: 0, enemy_max_hp: 100,
  combat_log: [], status: 'player_turn',
})

const playerHpPercent = computed(() => {
  if (!battleState.value.player_max_hp) return 0
  return Math.max(0, (battleState.value.player_hp / battleState.value.player_max_hp) * 100)
})

const enemyHpPercent = computed(() => {
  if (!battleState.value.enemy_max_hp) return 0
  return Math.max(0, (battleState.value.enemy_hp / battleState.value.enemy_max_hp) * 100)
})

const levelClass = (lvl) => `level-${lvl}`
const opponentAvatar = (lvl) => {
  const map = { 1: '👦', 2: '⚔️', 3: '🗡️', 4: '💀', 5: '👑' }
  return map[lvl] || '⚔️'
}

const loadTournament = async () => {
  try {
    const resp = await fetch('/api/tournament')
    const data = await resp.json()
    if (data.success) {
      opponents.value = data.opponents
      entryFee.value = data.entry_fee
      streakRewards.value = data.streak_rewards || {}
      history.value = data.history || []
    }
  } catch (e) {
    console.error('加载竞技场失败', e)
  }
}

const startBattle = async (opp) => {
  try {
    const resp = await fetch('/api/tournament/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ opponent_id: opp.opponent_id }),
    })
    const data = await resp.json()
    if (data.success) {
      currentBattle.value = data
      battleState.value = data.combat_state
      isFighting.value = true
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

const doAction = async (action) => {
  if (!currentBattle.value) return
  try {
    const result = await gameStore.wsCall('tournament_combat', { action })
    if (result?.success) {
      if (result.combat_state) {
        battleState.value = result.combat_state
      }
      if (result.combat_end) {
        ElMessage.success(result.message)
        currentBattle.value = null
        isFighting.value = false
        await loadTournament()
      } else {
        if (result.message) ElMessage.info(result.message)
      }
    } else {
      ElMessage.error(result?.message || '战斗失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

onMounted(() => {
  loadTournament()
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

.opponents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.opponent-card {
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s;
}

.opponent-card:hover {
  border-color: #d4a464;
}

.level-1 { border-left: 3px solid #4caf50; }
.level-2 { border-left: 3px solid #2196f3; }
.level-3 { border-left: 3px solid #ff9800; }
.level-4 { border-left: 3px solid #f44336; }
.level-5 { border-left: 3px solid #9c27b0; }

.opponent-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.opponent-avatar {
  font-size: 32px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(212, 164, 100, 0.1);
  border-radius: 50%;
}

.opponent-info h3 {
  margin: 0;
  color: #e8e0d0;
  font-size: 15px;
}

.level-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.1);
  color: #aaa;
}

.opponent-stats {
  display: flex;
  gap: 12px;
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

.opponent-rewards {
  display: flex;
  gap: 12px;
  font-size: 12px;
  margin: 8px 0;
}

.reward {
  color: #d4a464;
}

.fight-btn {
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

.fight-btn:hover:not(:disabled) {
  opacity: 0.85;
}

.fight-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.battle-section {
  margin-top: 20px;
}

.battle-arena {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 16px;
}

.fighter {
  flex: 1;
  text-align: center;
}

.fighter-name {
  font-size: 16px;
  font-weight: bold;
  color: #e8e0d0;
  margin-bottom: 8px;
}

.hp-bar {
  position: relative;
  height: 24px;
  background: #1a1a2e;
  border-radius: 12px;
  overflow: hidden;
}

.hp-fill {
  height: 100%;
  transition: width 0.3s;
  border-radius: 12px;
}

.hp-player { background: linear-gradient(90deg, #4caf50, #8bc34a); }
.hp-enemy { background: linear-gradient(90deg, #f44336, #ff5722); }

.hp-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  color: #fff;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
}

.vs {
  font-size: 24px;
  font-weight: bold;
  color: #d4a464;
}

.combat-log {
  max-height: 200px;
  overflow-y: auto;
  padding: 12px;
  background: rgba(10, 10, 20, 0.8);
  border-radius: 6px;
  margin-bottom: 16px;
}

.log-entry {
  font-size: 13px;
  color: #aaa;
  padding: 2px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.battle-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 10px 20px;
  background: rgba(212, 164, 100, 0.2);
  border: 1px solid #d4a464;
  border-radius: 6px;
  color: #d4a464;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.action-btn:hover {
  background: rgba(212, 164, 100, 0.4);
}

.streak-rewards {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.streak-card {
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
  min-width: 140px;
}

.streak-count {
  font-size: 18px;
  font-weight: bold;
  color: #d4a464;
}

.streak-title {
  font-size: 13px;
  color: #e8e0d0;
  margin: 4px 0;
}

.streak-bonus {
  font-size: 12px;
  color: #4caf50;
}

.history-list {
  max-height: 300px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 13px;
}

.history-item.win { color: #4caf50; }
.history-item.lose { color: #f44336; }

.result-icon { font-size: 16px; }
.opponent-name { flex: 1; color: #e8e0d0; }
.reward-text { color: #d4a464; }
.streak-text { color: #ff9800; }
</style>
